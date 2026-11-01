import pytest
from algorithms.pathfinding.static_dijkstra import StaticDijkstra
from cases.scenario_loader import ScenarioLoader
from config.settings import DEFAULT_YAML_SCENARIO
from core.simulation_runner import SimulationRunner

SPINE = [0, 1, 2, 3, 4, 5, 6, 7]
ALT = [0, 1, 8, 9, 10, 4, 5, 6, 7]


@pytest.fixture
def loaded_scenario():
    """Fixture: loader, model graf, dan execution plan dari case_01."""
    loader = ScenarioLoader(DEFAULT_YAML_SCENARIO)
    model = loader.build_graph_model()
    plan = loader.get_execution_plan()
    return loader, model, plan


def _step0_events(plan):
    return [e for e in plan["events"] if e.get("step", 1) == 0]


def _timeline_events(plan):
    return [e for e in plan["events"] if e.get("step", 1) != 0]


def _event_data(event, plan):
    data = {"type": event["type"], "start": plan["start_node"], "goal": plan["goal_node"]}
    if "target_edge" in event:
        data["edge"] = tuple(event["target_edge"])
    if "target_node" in event:
        data["target_node"] = event["target_node"]
    if "new_weight" in event:
        data["new_weight"] = event["new_weight"]
    return data


def test_rute_awal_memperhitungkan_keadaan_awal(loaded_scenario):
    """Rute awal harus sudah menghindari blocker step 0 dan memakai bobot genangan."""
    loader, model, plan = loaded_scenario
    solver = StaticDijkstra(model)
    solver.apply_initial_state([_event_data(e, plan) for e in _step0_events(plan)])

    path, cost = solver.run(plan["start_node"], plan["goal_node"])

    assert path == SPINE
    assert abs(cost - 18.97) < 0.01, f"cost awal salah: {cost}"


def test_urutan_event_lengkap_melalui_runner(loaded_scenario):
    """Seluruh timeline event menghasilkan urutan rute sesuai ground truth."""
    loader, model, plan = loaded_scenario
    solver = StaticDijkstra(model)
    runner = SimulationRunner(solver=solver, plan=plan, metadata=loader.get_metadata())
    result = runner.execute()

    assert result.initial_path == SPINE
    assert abs(result.initial_cost - 18.97) < 0.01

    expected = [
        ("BLOCK_NODE", [], float("inf")),
        ("UNBLOCK_EDGE", [], float("inf")),
        ("UNBLOCK_NODE", ALT, 25.55),
        ("UNBLOCK_NODE", SPINE, 18.97),
        ("DYNAMIC_EDGE_WEIGHT", SPINE, 14.67),
    ]
    assert len(result.reroutes) == 5
    for reroute, (etype, path, cost) in zip(result.reroutes, expected):
        assert reroute.event_type == etype
        assert reroute.path == path, f"{etype}: {reroute.path} != {path}"
        if cost == float("inf"):
            assert reroute.cost == float("inf")
        else:
            assert abs(reroute.cost - cost) < 0.01


def test_kobra_bergerombol_memutus_rute(loaded_scenario):
    """BLOCK_NODE pada simpang Taman Raya memutus koridor utama dan alternatif."""
    loader, model, plan = loaded_scenario
    solver = StaticDijkstra(model)
    solver.apply_initial_state([_event_data(e, plan) for e in _step0_events(plan)])
    solver.run(plan["start_node"], plan["goal_node"])

    event = _timeline_events(plan)[0]
    assert event["type"] == "BLOCK_NODE"
    path, cost = solver.handle_dynamic_event(_event_data(event, plan))

    assert path == []
    assert cost == float("inf")


def test_sampah_dibersihkan_belum_cukup(loaded_scenario):
    """Setelah sampah dibersihkan, kobra diam K2 di node 9 masih memutus koridor alternatif."""
    loader, model, plan = loaded_scenario
    solver = StaticDijkstra(model)
    solver.apply_initial_state([_event_data(e, plan) for e in _step0_events(plan)])

    for event in _timeline_events(plan)[:2]:
        path, cost = solver.handle_dynamic_event(_event_data(event, plan))

    assert path == []
    assert cost == float("inf")


def test_reroute_via_koridor_alternatif(loaded_scenario):
    """Setelah K2 diusir, rute aman memutar lewat Kemuning Raya dan Mista Raya."""
    loader, model, plan = loaded_scenario
    solver = StaticDijkstra(model)
    solver.apply_initial_state([_event_data(e, plan) for e in _step0_events(plan)])

    for event in _timeline_events(plan)[:3]:
        path, cost = solver.handle_dynamic_event(_event_data(event, plan))

    assert path == ALT
    assert abs(cost - 25.55) < 0.01


def test_blokir_ruas_memblokir_dua_arah(loaded_scenario):
    """BLOCK_EDGE pada ruas dua_arah harus memblokir kedua arah."""
    loader, model, plan = loaded_scenario
    solver = StaticDijkstra(model)
    solver.apply_initial_state([_event_data(e, plan) for e in _step0_events(plan)])

    assert (9, 10) in solver.blocked_edges
    assert (10, 9) in solver.blocked_edges


def test_genangan_membengkakkan_bobot_dua_arah(loaded_scenario):
    """Surge genangan diterapkan ke kedua arah ruas tergenang."""
    loader, model, plan = loaded_scenario
    solver = StaticDijkstra(model)
    solver.apply_initial_state([_event_data(e, plan) for e in _step0_events(plan)])

    G = model.nx_graph
    assert G[4][5]["weight"] == 6.45
    assert G[5][4]["weight"] == 6.45


def test_banjir_surut_mengembalikan_bobot(loaded_scenario):
    """Event restore di step 6 mengembalikan bobot ruas genangan ke normal."""
    loader, model, plan = loaded_scenario
    solver = StaticDijkstra(model)
    solver.apply_initial_state([_event_data(e, plan) for e in _step0_events(plan)])

    for event in _timeline_events(plan):
        path, cost = solver.handle_dynamic_event(_event_data(event, plan))

    G = model.nx_graph
    assert G[4][5]["weight"] == 2.15
    assert path == SPINE
    assert abs(cost - 14.67) < 0.01


def test_tracing_logs_tercatat(loaded_scenario):
    """Memastikan log kuantitatif terekam konsisten."""
    loader, model, plan = loaded_scenario
    solver = StaticDijkstra(model)
    solver.apply_initial_state([_event_data(e, plan) for e in _step0_events(plan)])
    solver.run(plan["start_node"], plan["goal_node"])

    assert solver.step_count > 0
    assert len(solver.delta_logs) == solver.step_count
    event_types = [log["event_type"] for log in solver.delta_logs]
    assert "INITIALIZATION" in event_types, "log INITIALIZATION tidak ditemukan"
    assert "PATH_FOUND" in event_types, "log PATH_FOUND tidak ditemukan"
