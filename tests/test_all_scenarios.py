from pathlib import Path

import pytest

from algorithms.pathfinding.static_dijkstra import StaticDijkstra
from algorithms.registry import AlgorithmRegistry
from cases.scenario_loader import ScenarioLoader
from config.settings import CASES_DIR, DEFAULT_ALGORITHM, SCENARIO_FILE_PATTERNS


def _discover_scenario_files() -> list:
    files = []
    for pattern in SCENARIO_FILE_PATTERNS:
        files.extend(CASES_DIR.glob(pattern))
    return sorted(set(files))


SCENARIO_FILES = _discover_scenario_files()


def _event_data(event, plan):
    data = {"type": event["type"], "start": plan["start_node"], "goal": plan["goal_node"]}
    if "target_edge" in event:
        data["edge"] = tuple(event["target_edge"])
    if "target_node" in event:
        data["target_node"] = event["target_node"]
    if "new_weight" in event:
        data["new_weight"] = event["new_weight"]
    return data


@pytest.mark.parametrize("yaml_path", SCENARIO_FILES, ids=lambda p: p.stem)
def test_scenario_pipeline_contract(yaml_path: Path):
    """Audit kontrak data-driven untuk setiap skenario: scoped, valid, aman, terekam."""
    loader = ScenarioLoader(yaml_path)

    metadata = loader.get_metadata()
    assert metadata.get("case_id"), f"{yaml_path.name}: case_id tidak ditemukan"
    assert metadata.get("title"), f"{yaml_path.name}: title tidak ditemukan"

    problem = loader.get_problem()
    assert problem.get("objectives"), f"{yaml_path.name}: objectives kosong"
    assumptions = problem.get("assumptions", {})
    for entity in ("snakes", "trash", "flood"):
        assert entity in assumptions, f"{yaml_path.name}: assumptions tanpa {entity}"
    assert problem.get("constraints"), f"{yaml_path.name}: constraints kosong"

    plan = loader.get_execution_plan()
    assert "start_node" in plan, f"{yaml_path.name}: start_node tidak ditemukan"
    assert "goal_node" in plan, f"{yaml_path.name}: goal_node tidak ditemukan"

    model = loader.build_graph_model()
    G = model.nx_graph
    assert len(G.nodes) > 0, f"{yaml_path.name}: graf tanpa node"
    assert len(G.edges) > 0, f"{yaml_path.name}: graf tanpa edge"
    assert plan["start_node"] in G.nodes, f"{yaml_path.name}: start_node tidak ada di graf"
    assert plan["goal_node"] in G.nodes, f"{yaml_path.name}: goal_node tidak ada di graf"

    loader.validate(model)

    solver = AlgorithmRegistry.create(DEFAULT_ALGORITHM, model)

    step0 = [e for e in plan.get("events", []) if e.get("step", 1) == 0]
    if step0 and hasattr(solver, "apply_initial_state"):
        solver.apply_initial_state([_event_data(e, plan) for e in step0])

    path, cost = solver.run(plan["start_node"], plan["goal_node"])
    assert isinstance(path, list), f"{yaml_path.name}: rute awal bukan list"
    if path:
        assert path[0] == plan["start_node"], f"{yaml_path.name}: rute tidak mulai dari start"
        assert path[-1] == plan["goal_node"], f"{yaml_path.name}: rute tidak berakhir di goal"

    supported_types = getattr(solver, "SUPPORTED_EVENT_TYPES", None)
    timeline = [e for e in plan.get("events", []) if e.get("step", 1) != 0]
    for idx, event in enumerate(timeline, 1):
        assert event.get("type"), f"{yaml_path.name}: event #{idx} tanpa 'type'"
        assert event.get("description"), f"{yaml_path.name}: event #{idx} tanpa 'description'"

        if supported_types is not None and event["type"] not in supported_types:
            if "target_edge" in event:
                u, v = event["target_edge"]
                assert G.has_edge(u, v), (
                    f"{yaml_path.name}: event #{idx} menunjuk edge ({u}, {v}) yang tidak ada"
                )
            if "target_node" in event:
                assert event["target_node"] in G.nodes, (
                    f"{yaml_path.name}: event #{idx} menunjuk node tidak dikenal"
                )
            continue

        new_path, new_cost = solver.handle_dynamic_event(_event_data(event, plan))
        assert isinstance(new_path, list), (
            f"{yaml_path.name}: rute pasca-event #{idx} bukan list"
        )
        if new_path:
            assert new_path[0] == plan["start_node"], (
                f"{yaml_path.name}: rute pasca-event #{idx} tidak mulai dari start"
            )
            assert new_path[-1] == plan["goal_node"], (
                f"{yaml_path.name}: rute pasca-event #{idx} tidak berakhir di goal"
            )

    assert solver.step_count > 0, f"{yaml_path.name}: delta log kosong"
    assert len(solver.delta_logs) == solver.step_count, (
        f"{yaml_path.name}: jumlah log tidak sinkron dengan step_count"
    )


def test_static_dijkstra_terdaftar_di_registry():
    """Memastikan solver baseline terdaftar dan bisa dibuat lewat factory."""
    from core.graph_model import SpatialGraphModel

    solver = AlgorithmRegistry.create("pathfinding", SpatialGraphModel())
    assert isinstance(solver, StaticDijkstra)
