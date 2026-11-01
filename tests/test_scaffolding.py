import traceback
from typing import Type

from cases.scenario_loader import ScenarioLoader
from core.base_algorithm import BaseGraphAlgorithm


class SOTAScaffoldingAuditor:
    """Modul Scaffolding untuk mendiagnosis dan membedah eror pada algoritma SOTA mahasiswa."""

    def __init__(self, algorithm_class: Type[BaseGraphAlgorithm], yaml_path: str):
        self.algorithm_class = algorithm_class
        self.yaml_path = yaml_path
        self.loader = ScenarioLoader(yaml_path)
        self.metadata = self.loader.get_metadata()
        self.plan = self.loader.get_execution_plan()
        self.model = self.loader.build_graph_model()
        self.solver = None

    def run_full_diagnostic(self) -> bool:
        print(f"\n============================================================")
        print(f"  DIAGNOSTIC AUDIT: {self.algorithm_class.__name__}")
        print(f"  Case: {self.metadata.get('title', 'Unknown Case')}")
        print(f"============================================================\n")

        if not self._audit_class_structure():
            return False
        if not self._audit_initial_run():
            return False
        if not self._audit_dynamic_events():
            return False
        if not self._audit_trace_integrity():
            return False

        print(f"\n[PASSED] ALL TESTS PASSED! Algoritma Anda Valid & Robust.")
        return True

    def _audit_class_structure(self) -> bool:
        print("[STAGE 1/4] Auditing Class Inheritance & Interface...")
        if not issubclass(self.algorithm_class, BaseGraphAlgorithm):
            print("FAIL: Kelas harus menuruni 'BaseGraphAlgorithm'!")
            return False
        try:
            self.solver = self.algorithm_class(self.model)
            print("  OK Class Instantiation Success.")
            return True
        except Exception as e:
            print(f"FAIL: Eror saat inisialisasi kelas {self.algorithm_class.__name__}: {e}")
            traceback.print_exc()
            return False

    def _audit_initial_run(self) -> bool:
        print("\n[STAGE 2/4] Auditing Initial Search (Phase 1)...")
        start, goal = self.plan["start_node"], self.plan["goal_node"]
        try:
            step0 = [e for e in self.plan.get("events", []) if e.get("step", 1) == 0]
            if step0 and hasattr(self.solver, "apply_initial_state"):
                self.solver.apply_initial_state(
                    [self._event_data(e) for e in step0]
                )
            path, cost = self.solver.run(start, goal)
            if not isinstance(path, list):
                print(f"FAIL: Rute tidak valid: {path}")
                return False
            if path:
                if path[0] != start or path[-1] != goal:
                    print(
                        f"FAIL: Rute salah! Start={path[0]} (harus {start}), "
                        f"Goal={path[-1]} (harus {goal})."
                    )
                    return False
            print(f"  OK Initial Path: {path} | Cost: {cost}")
            return True
        except Exception as e:
            print(f"FAIL: Crash pada method run():")
            traceback.print_exc()
            return False

    def _audit_dynamic_events(self) -> bool:
        print("\n[STAGE 3/4] Auditing Dynamic Event Handling (Phase 2)...")
        start, goal = self.plan["start_node"], self.plan["goal_node"]

        timeline = [e for e in self.plan.get("events", []) if e.get("step", 1) != 0]
        for idx, event in enumerate(timeline, 1):
            print(f"  -> Testing Event #{idx}: {event['type']} (entity {event.get('entity_id')})")
            try:
                path, cost = self.solver.handle_dynamic_event(self._event_data(event))
                if not isinstance(path, list):
                    print(f"FAIL pada Event #{idx}: Rute tidak valid: {path}")
                    return False
                if path and (path[0] != start or path[-1] != goal):
                    print(
                        f"FAIL pada Event #{idx}: Rute tidak dari start ke goal: {path}"
                    )
                    return False
                print(f"  OK Event #{idx} -> Path: {path} | Cost: {cost}")
            except Exception as e:
                print(f"FAIL: Crash pada handle_dynamic_event() Event #{idx}:")
                traceback.print_exc()
                return False
        return True

    def _audit_trace_integrity(self) -> bool:
        print("\n[STAGE 4/4] Auditing Quantitative Trace Log Integrity...")
        if self.solver.step_count == 0 or len(self.solver.delta_logs) == 0:
            print("FAIL: 'delta_logs' kosong! Panggil 'self.log_step()' di dalam algoritma Anda.")
            return False
        print(f"  OK Trace Log Integrity. Total Logged Steps: {self.solver.step_count}")
        return True

    def _event_data(self, event: dict) -> dict:
        data = {
            "type": event.get("type"),
            "start": self.plan["start_node"],
            "goal": self.plan["goal_node"],
        }
        if "target_edge" in event:
            data["edge"] = tuple(event["target_edge"])
        if "target_node" in event:
            data["target_node"] = event["target_node"]
        if "new_weight" in event:
            data["new_weight"] = event["new_weight"]
        return data


# Fungsi tes otomatis untuk PyTest
def test_static_dijkstra_baseline():
    from algorithms.pathfinding.static_dijkstra import StaticDijkstra
    from config.settings import DEFAULT_YAML_SCENARIO

    auditor = SOTAScaffoldingAuditor(StaticDijkstra, str(DEFAULT_YAML_SCENARIO))
    assert auditor.run_full_diagnostic() is True
