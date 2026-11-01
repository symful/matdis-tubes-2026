import pytest
from cases.fishbone_parser import FishboneParser, FISHBONE_6M
from cases.scenario_loader import ScenarioLoader
from config.settings import DEFAULT_YAML_SCENARIO


@pytest.fixture
def parser():
    loader = ScenarioLoader(DEFAULT_YAML_SCENARIO)
    return FishboneParser(loader.get_fishbone())


def test_tiga_tabel_terbaca(parser):
    """Memastikan tiga tabel fishbone terbaca: non-6M dan dua varian 6M."""
    tables = parser.get_tables()
    assert len(tables) == 3

    variants = [t["variant"] for t in tables]
    assert variants == ["non6m", "6m", "6m"]

    for table in tables:
        assert len(table["categories"]) == 6
        assert table["problem"]


def test_kategori_non6m_lahir_dari_kasus(parser):
    """Varian non-6M memakai kategori yang lahir dari kasus, bukan kategori baku."""
    tables = {t["key"]: t for t in parser.get_tables()}
    names = [c["name"] for c in tables["non6m_risk_kobra"]["categories"]]
    assert "Pemicu Banjir" in names
    assert "Pergerakan Kobra" in names
    assert "MAN" not in names


def test_validate_6m_lengkap(parser):
    """Validasi 6M berhasil bila keenam kategori baku ada."""
    assert parser.validate() is True


def test_validate_menolak_6m_kurang(parser):
    """Validasi menolak tabel 6M yang kehilangan kategori baku."""
    parser.data["risk_6m"]["categories"].pop("ENVIRONMENT")
    with pytest.raises(ValueError):
        parser.validate()


def test_to_markdown_merender_tabel(parser):
    """Render markdown memuat nama kategori dan penyebab."""
    md = parser.to_markdown()
    assert "MAN" in md
    assert "Pemicu Banjir" in md
    assert "Warga belum tahu rute" in md
    assert "Sarang kebanjiran" in md


def test_konstanta_6m_baku():
    """Enam kategori baku fishbone sesuai urutan 6M."""
    assert set(FISHBONE_6M) == {
        "MAN",
        "MACHINE",
        "METHOD",
        "MATERIAL",
        "ENVIRONMENT",
        "MEASUREMENT",
    }
