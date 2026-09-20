import sys
from algorithms.pathfinding.static_dijkstra import StaticDijkstra
from cases.scenario_loader import ScenarioLoader
from config.settings import DEFAULT_YAML_SCENARIO
from core.visualizer import SimpleGraphVisualizer


def run_simulation(yaml_path: str):
    # 1. Load Scenario
    loader = ScenarioLoader(yaml_path)
    metadata = loader.get_metadata()
    graph_model = loader.build_graph_model()
    plan = loader.get_execution_plan()

    start_node = plan["start_node"]
    goal_node = plan["goal_node"]

    # 2. Inisialisasi Visualizer & Solver
    viz = SimpleGraphVisualizer(graph_model.nx_graph)
    solver = StaticDijkstra(graph_model)

    print(f"=== RUNNING SIMULATION: {metadata['title']} ===")
    print(f"Algorithm: {solver.__class__.__name__}")

    # 3. Phase 1: Rute Awal
    path_1, cost_1 = solver.run(start_node, goal_node)
    print(f"-> Rute Awal  : {path_1} (Cost: {cost_1})")

    viz.draw_snapshot(
        title=f"Kondisi Normal - {metadata['title']}\nRute Awal: {path_1} (Cost: {cost_1})",
        active_path=path_1,
    )

    # 4. Phase 2: Dynamic Event Injection
    for event in plan.get("events", []):
        print(f"\n[EVENT INJECTED] {event['description']}")

        target_edge = tuple(event["target_edge"])
        event_data = {
            "edge": target_edge,
            "new_weight": event["new_weight"],
            "start": start_node,
            "goal": goal_node,
        }

        path_2, cost_2 = solver.handle_dynamic_event(event_data)
        print(f"-> Rute Baru  : {path_2} (Cost: {cost_2})")

        viz.draw_snapshot(
            title=f"Event: {event['description']}\nRute Baru: {path_2} (Cost: {cost_2})",
            active_path=path_2,
            highlighted_edge=target_edge,
        )

    # 5. Export Raw Trace JSON ke folder output/
    output_filename = f"output_{metadata['case_id']}.json"
    saved_path = solver.export_trace_json(
        output_filename, metadata={**metadata, "algorithm": solver.__class__.__name__}
    )

    print(f"\n[SUCCESS] Quantitative Trace Log exported to: {saved_path}")


if __name__ == "__main__":
    yaml_file = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_YAML_SCENARIO)
    run_simulation(yaml_file)