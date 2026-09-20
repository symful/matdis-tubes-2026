import sys
import time
from algorithms.pathfinding.static_dijkstra import StaticDijkstra
from cases.scenario_loader import ScenarioLoader
from config.settings import DEFAULT_YAML_SCENARIO


def run_benchmark(yaml_path: str):
    loader = ScenarioLoader(yaml_path)
    metadata = loader.get_metadata()
    graph_model = loader.build_graph_model()
    plan = loader.get_execution_plan()

    start_node = plan["start_node"]
    goal_node = plan["goal_node"]

    solver = StaticDijkstra(graph_model)

    print(f"=== RUNNING BENCHMARK METRICS: {metadata['title']} ===")

    # Measure Initial Run Time
    t_start = time.perf_counter()
    path_1, cost_1 = solver.run(start_node, goal_node)
    t_initial_ms = (time.perf_counter() - t_start) * 1000

    # Measure Event Re-routing Time
    t_event_total_ms = 0.0
    for event in plan.get("events", []):
        event_data = {
            "edge": tuple(event["target_edge"]),
            "new_weight": event["new_weight"],
            "start": start_node,
            "goal": goal_node,
        }
        t_event_start = time.perf_counter()
        solver.handle_dynamic_event(event_data)
        t_event_total_ms += (time.perf_counter() - t_event_start) * 1000

    print("\n------------------ BENCHMARK RESULTS ------------------")
    print(f" Algorithm Class      : {solver.__class__.__name__}")
    print(f" Total Logged Steps   : {solver.step_count} steps")
    print(f" Initial Search Time  : {t_initial_ms:.4f} ms")
    print(f" Re-routing Time      : {t_event_total_ms:.4f} ms")
    print("-------------------------------------------------------")


if __name__ == "__main__":
    yaml_file = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_YAML_SCENARIO)
    run_benchmark(yaml_file)