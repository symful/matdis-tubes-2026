import pytest
from cases.scenario_loader import ScenarioLoader
from config.settings import DEFAULT_YAML_SCENARIO
from core.graph_model import SpatialGraphModel


@pytest.fixture
def loader():
    return ScenarioLoader(DEFAULT_YAML_SCENARIO)


def test_scenario_loader_file_not_found():
    """Memastikan loader melempar FileNotFoundError jika path YAML tidak valid."""
    with pytest.raises(FileNotFoundError):
        ScenarioLoader("invalid/path/non_existent.yaml")


def test_scoped_sections_terbaca(loader):
    """Memastikan bagian ruang lingkup soal terbaca: problem, entities, fishbone, sample."""
    problem = loader.get_problem()
    assert problem["objectives"], "objectives kosong"
    assert "statement" in problem
    assert "constraints" in problem

    assumptions = problem["assumptions"]
    assert assumptions["snakes"]["movable"] is True
    assert assumptions["trash"]["movable"] is False
    assert assumptions["trash"]["clearable"] is True
    assert assumptions["flood"]["effect"] == "weight_surge"
    assert assumptions["flood"]["passable"] is True

    entities = loader.get_entities()
    assert len(entities["snakes"]) == 2
    assert len(entities["trash"]) == 1
    assert len(entities["flood"]) == 1

    fishbone = loader.get_fishbone()
    assert set(fishbone.keys()) == {"non6m_risk_kobra", "path_6m", "risk_6m"}

    assert "note" in loader.get_sample()


def test_build_graph_model_dua_arah(loader):
    """Memastikan ruas dua_arah menghasilkan edge bolak-balik dan atribut jalan tersimpan."""
    model = loader.build_graph_model()
    G = model.nx_graph

    assert isinstance(model, SpatialGraphModel)
    assert len(G.nodes) == 13
    assert len(G.edges) == 28, f"14 ruas dua_arah harus jadi 28 edge searah, didapat {len(G.edges)}"

    assert G.has_edge(1, 0) and G.has_edge(0, 1)
    assert G[0][1]["weight"] == 0.42
    assert G[0][1]["street"] == "Jl. Edelweis I"
    assert G[4][5]["distance_m"] == 161.4
    assert G[4][5]["flooded"] is True


def test_validate_menolak_window_node_tak_dikenal(loader):
    """Memastikan validasi menolak window ular yang menunjuk node di luar graf."""
    loader.data["entities"]["snakes"][0]["windows"][0]["node"] = 999
    with pytest.raises(ValueError):
        loader.validate()


def test_validate_menolak_event_entity_id_tak_terdaftar(loader):
    """Memastikan validasi menolak event yang merujuk entity_id yang tidak ada."""
    loader.data["execution_plan"]["events"][0]["entity_id"] = "X9"
    with pytest.raises(ValueError):
        loader.validate()


def test_validate_menolak_target_edge_tak_dikenal(loader):
    """Memastikan validasi menolak event yang menunjuk edge yang tidak ada."""
    loader.data["execution_plan"]["events"][3]["target_edge"] = [0, 99]
    with pytest.raises(ValueError):
        loader.validate()


def test_metadata_lengkap(loader):
    """Memastikan metadata kasus lengkap: case_id, title, author."""
    metadata = loader.get_metadata()
    assert metadata["case_id"] == "case_01_kobra_banjir"
    assert metadata["title"]
    assert metadata["author"]
