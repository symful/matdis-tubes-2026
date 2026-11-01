import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.base_algorithm import BaseGraphAlgorithm


@dataclass
class RerouteResult:
    description: str
    target_edge: Optional[Tuple[int, int]]
    new_weight: Optional[float]
    path: List[int]
    cost: float
    elapsed_ms: float
    event_type: str = ""
    entity_id: Optional[str] = None


@dataclass
class SimulationResult:
    metadata: Dict[str, Any]
    algorithm_name: str
    initial_path: List[int]
    initial_cost: float
    initial_elapsed_ms: float
    reroutes: List[RerouteResult] = field(default_factory=list)
    skipped_events: List[Dict[str, Any]] = field(default_factory=list)


class SimulationObserver:

    def on_initial_route(self, result: SimulationResult) -> None:
        pass

    def on_reroute(self, result: SimulationResult, reroute: RerouteResult) -> None:
        pass

    def on_event_skipped(self, result: SimulationResult, event: Dict[str, Any]) -> None:
        pass

    def on_complete(self, result: SimulationResult) -> None:
        pass


class SimulationRunner:

    def __init__(
        self,
        solver: BaseGraphAlgorithm,
        plan: Dict[str, Any],
        metadata: Dict[str, Any],
        observers: Optional[List[SimulationObserver]] = None,
    ):
        self.solver = solver
        self.plan = plan
        self.metadata = metadata
        self.observers: List[SimulationObserver] = list(observers or [])

    def attach(self, observer: SimulationObserver) -> None:
        self.observers.append(observer)

    def execute(self) -> SimulationResult:
        start_node = self.plan["start_node"]
        goal_node = self.plan["goal_node"]

        # Event step 0 = keadaan awal (blocker statis, genangan) diterapkan
        # sebelum rute awal dihitung.
        events = self.plan.get("events", [])
        initial_events = [e for e in events if e.get("step", 1) == 0]
        timeline = [e for e in events if e.get("step", 1) != 0]

        if initial_events and hasattr(self.solver, "apply_initial_state"):
            self.solver.apply_initial_state(
                [self._event_data(e, start_node, goal_node) for e in initial_events]
            )

        t_start = time.perf_counter()
        path, cost = self.solver.run(start_node, goal_node)
        initial_elapsed_ms = (time.perf_counter() - t_start) * 1000

        result = SimulationResult(
            metadata=self.metadata,
            algorithm_name=self.solver.__class__.__name__,
            initial_path=path,
            initial_cost=cost,
            initial_elapsed_ms=initial_elapsed_ms,
        )
        self._notify("on_initial_route", result)

        supported_types = getattr(self.solver, "SUPPORTED_EVENT_TYPES", None)
        for event in timeline:
            if supported_types is not None and event.get("type") not in supported_types:
                result.skipped_events.append(event)
                self._notify("on_event_skipped", result, event)
                continue
            reroute = self._execute_event(event, start_node, goal_node)
            result.reroutes.append(reroute)
            self._notify("on_reroute", result, reroute)

        self._notify("on_complete", result)
        return result

    def _execute_event(
        self, event: Dict[str, Any], start_node: int, goal_node: int
    ) -> RerouteResult:
        event_data = self._event_data(event, start_node, goal_node)

        t_start = time.perf_counter()
        path, cost = self.solver.handle_dynamic_event(event_data)
        elapsed_ms = (time.perf_counter() - t_start) * 1000

        return RerouteResult(
            description=event.get("description", ""),
            target_edge=tuple(event["target_edge"]) if "target_edge" in event else None,
            new_weight=event.get("new_weight"),
            path=path,
            cost=cost,
            elapsed_ms=elapsed_ms,
            event_type=event.get("type", ""),
            entity_id=event.get("entity_id"),
        )

    @staticmethod
    def _event_data(event: Dict[str, Any], start_node: int, goal_node: int) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": event.get("type"),
            "start": start_node,
            "goal": goal_node,
        }
        if "entity_id" in event:
            data["entity_id"] = event["entity_id"]
        if "target_edge" in event:
            data["edge"] = tuple(event["target_edge"])
        if "target_node" in event:
            data["target_node"] = event["target_node"]
        if "new_weight" in event:
            data["new_weight"] = event["new_weight"]
        return data

    def _notify(self, hook: str, *args) -> None:
        for observer in self.observers:
            getattr(observer, hook)(*args)
