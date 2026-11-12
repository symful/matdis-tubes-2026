"""Record every simulation state so the desktop app can replay it."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import networkx as nx

import algorithms  # noqa: F401  (registers StaticDijkstra in the registry)
from algorithms.registry import AlgorithmRegistry, resolve_algorithm_key
from cases.scenario_loader import ScenarioLoader
from config.settings import DEFAULT_ALGORITHM
from core.simulation_runner import (
    RerouteResult,
    SimulationObserver,
    SimulationResult,
    SimulationRunner,
)


@dataclass
class Snapshot:
    index: int
    label: str
    step: int
    event_type: str
    entity_id: Optional[str]
    description: str
    path: List[int]
    cost: float
    meters: float
    blocked_nodes: List[int]
    blocked_edges: List[Tuple[int, int]]
    weights: Dict[Tuple[int, int], float]
    active_blockers: List[str]
    blocker_map: Dict[str, str] = field(default_factory=dict)
    target_node: Optional[int] = None
    target_edge: Optional[Tuple[int, int]] = None
    new_weight: Optional[float] = None


@dataclass
class ScenarioView:
    yaml_path: Path
    metadata: Dict[str, Any]
    plan: Dict[str, Any]
    graph: nx.DiGraph
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    node_by_id: Dict[int, Dict[str, Any]]
    edge_meta: Dict[Tuple[int, int], Dict[str, Any]]
    flood_windows: List[Dict[str, Any]]
    entities: Dict[str, Dict[str, Any]]
    entity_labels: Dict[str, str]
    network_edges: List[Dict[str, Any]] = field(default_factory=list)
    abstract: bool = False
    snapshots: List[Snapshot] = field(default_factory=list)


class SnapshotRecorder(SimulationObserver):
    """Observer that stores one replayable snapshot per simulation state."""

    def __init__(self, solver, plan: Dict[str, Any]):
        self.solver = solver
        self.graph = solver.graph
        self.plan = plan
        self.snapshots: List[Snapshot] = []
        self._initial_events = [e for e in plan.get("events", []) if e.get("step", 1) == 0]
        self._timeline = [e for e in plan.get("events", []) if e.get("step", 1) != 0]
        self._cursor = 0
        self._node_entity: Dict[int, Optional[str]] = {}
        self._edge_entity: Dict[Tuple[int, int], Optional[str]] = {}

    def on_initial_route(self, result: SimulationResult) -> None:
        for event in self._initial_events:
            self._track_entity(event)
        self._record(
            label="Keadaan awal (step 0)",
            step=0,
            event_type="INITIAL",
            entity_id=None,
            description=(
                "Blocker statis dan genangan dari event step 0 sudah diterapkan "
                "sebelum rute awal dihitung."
            ),
            path=result.initial_path,
            cost=result.initial_cost,
        )

    def on_reroute(self, result: SimulationResult, reroute: RerouteResult) -> None:
        event = self._timeline[self._cursor] if self._cursor < len(self._timeline) else {}
        self._cursor += 1
        self._track_entity(event)
        target_edge = tuple(event["target_edge"]) if "target_edge" in event else None
        self._record(
            label=f"Step {event.get('step', self._cursor)} \u2014 {reroute.event_type}",
            step=event.get("step", self._cursor),
            event_type=reroute.event_type,
            entity_id=reroute.entity_id,
            description=reroute.description,
            path=reroute.path,
            cost=reroute.cost,
            target_node=event.get("target_node"),
            target_edge=target_edge,
            new_weight=event.get("new_weight"),
        )

    def _track_entity(self, event: Dict[str, Any]) -> None:
        etype = event.get("type")
        entity_id = event.get("entity_id")
        if etype == "BLOCK_NODE":
            self._node_entity[event["target_node"]] = entity_id
        elif etype == "UNBLOCK_NODE":
            self._node_entity.pop(event.get("target_node"), None)
        elif etype == "BLOCK_EDGE":
            self._edge_entity[tuple(sorted(event["target_edge"]))] = entity_id
        elif etype == "UNBLOCK_EDGE":
            self._edge_entity.pop(tuple(sorted(event["target_edge"])), None)

    def _record(
        self,
        label: str,
        step: int,
        event_type: str,
        entity_id: Optional[str],
        description: str,
        path: List[int],
        cost: float,
        target_node: Optional[int] = None,
        target_edge: Optional[Tuple[int, int]] = None,
        new_weight: Optional[float] = None,
    ) -> None:
        active = [eid for eid in self._node_entity.values() if eid]
        active += [eid for eid in self._edge_entity.values() if eid]

        blocker_map: Dict[str, str] = {}
        for node_id, eid in self._node_entity.items():
            if eid:
                blocker_map[f"node:{node_id}"] = eid
        for (u, v), eid in self._edge_entity.items():
            if eid:
                blocker_map[f"edge:{u}-{v}"] = eid

        self.snapshots.append(
            Snapshot(
                index=len(self.snapshots),
                label=label,
                step=step,
                event_type=event_type,
                entity_id=entity_id,
                description=description,
                path=list(path or []),
                cost=cost,
                meters=self._path_meters(path),
                blocked_nodes=sorted(self.solver.blocked_nodes),
                blocked_edges=sorted(
                    {tuple(sorted(edge)) for edge in self.solver.blocked_edges}
                ),
                weights={
                    (u, v): data.get("weight", 1.0)
                    for u, v, data in self.graph.edges(data=True)
                },
                active_blockers=sorted(set(active)),
                blocker_map=blocker_map,
                target_node=target_node,
                target_edge=target_edge,
                new_weight=new_weight,
            )
        )

    def _path_meters(self, path: List[int]) -> float:
        total = 0.0
        for u, v in zip(path, path[1:]):
            if self.graph.has_edge(u, v):
                total += self.graph[u][v].get("distance_m", 0.0)
        return total


def load_network_edges(yaml_path: Path) -> List[Dict[str, Any]]:
    """Load the optional Overpass network snapshot that sits beside a case."""
    network_path = yaml_path.with_name(yaml_path.stem + ".network.json")
    if not network_path.exists():
        return []
    try:
        data = json.loads(network_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    nodes = {node["id"]: node for node in data.get("nodes", [])}
    edges: List[Dict[str, Any]] = []
    seen = set()
    for edge in data.get("edges", []):
        start = nodes.get(edge.get("from"))
        end = nodes.get(edge.get("to"))
        if start is None or end is None:
            continue
        start_pos = start.get("pos_m")
        end_pos = end.get("pos_m")
        if not start_pos or not end_pos:
            continue
        key = tuple(sorted((edge.get("from"), edge.get("to"))))
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "x1": float(start_pos[0]),
                "y1": float(start_pos[1]),
                "x2": float(end_pos[0]),
                "y2": float(end_pos[1]),
                "street": edge.get("street", ""),
                "highway": edge.get("highway", ""),
            }
        )
    return edges


def build_scenario_view_from_data(
    data: Dict[str, Any], base_path: Path, algorithm_key: Optional[str] = None
) -> ScenarioView:
    """Build a view from an in-memory scenario dict (used by runtime variants)."""
    return _build_view(ScenarioLoader(data), Path(base_path), algorithm_key)


def build_scenario_view(
    yaml_path: Union[str, Path], algorithm_key: Optional[str] = None
) -> ScenarioView:
    """Run a scenario once and return the graph plus every intermediate state."""
    yaml_path = Path(yaml_path)
    return _build_view(ScenarioLoader(yaml_path), yaml_path, algorithm_key)


def _build_view(
    loader: ScenarioLoader, yaml_path: Path, algorithm_key: Optional[str]
) -> ScenarioView:
    metadata = loader.get_metadata()
    plan = loader.get_execution_plan()
    model = loader.build_graph_model()

    key = resolve_algorithm_key(algorithm_key, plan, metadata, DEFAULT_ALGORITHM)
    solver = AlgorithmRegistry.create(key, model)

    recorder = SnapshotRecorder(solver, plan)
    runner = SimulationRunner(
        solver=solver, plan=plan, metadata=metadata, observers=[recorder]
    )
    runner.execute()

    nodes = loader.data.get("nodes", [])
    edges = loader.data.get("edges", [])
    node_by_id = {node["id"]: node for node in nodes}
    edge_meta: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for edge in edges:
        edge_meta[(edge["from"], edge["to"])] = edge
        edge_meta.setdefault((edge["to"], edge["from"]), edge)

    entities = loader.get_entities()
    entity_details: Dict[str, Dict[str, Any]] = {}
    for group in ("snakes", "trash", "flood"):
        for entity in entities.get(group, []):
            detail = dict(entity)
            detail["_group"] = group
            entity_details[entity["id"]] = detail

    flood_windows = []
    for flood in entities.get("flood", []):
        window = flood.get("window", {})
        flood_windows.append(
            {
                "edges": {
                    tuple(sorted(edge)) for edge in flood.get("submerged_edges", [])
                },
                "from_step": window.get("from_step", 0),
                "to_step": window.get("to_step", float("inf")),
                "entity_id": flood.get("id"),
                "surge_factor": flood.get("surge_factor"),
            }
        )
    entity_labels = {
        entity_id: detail.get("label", entity_id)
        for entity_id, detail in entity_details.items()
    }

    xs = [float(node["pos"][0]) for node in nodes if node.get("pos")]
    ys = [float(node["pos"][1]) for node in nodes if node.get("pos")]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 0.0) if xs and ys else 0.0

    return ScenarioView(
        yaml_path=yaml_path,
        metadata=metadata,
        plan=plan,
        graph=model.nx_graph,
        nodes=nodes,
        edges=edges,
        node_by_id=node_by_id,
        edge_meta=edge_meta,
        flood_windows=flood_windows,
        entities=entity_details,
        entity_labels=entity_labels,
        network_edges=load_network_edges(yaml_path),
        abstract=span < 100,
        snapshots=recorder.snapshots,
    )
