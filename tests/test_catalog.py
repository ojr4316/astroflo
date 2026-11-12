""" Star catalog with and without the (optional) ephemeris data files """
import os

import pytest

from astronomy import catalog as catalog_mod
from observation_context import Environment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def stars(star_table):
    return star_table


def make_catalog(monkeypatch, stars, ephemeris, asteroids=None):
    monkeypatch.setattr(catalog_mod, "load_stars", lambda: stars)
    monkeypatch.setattr(catalog_mod, "ephemeris_file", ephemeris)
    monkeypatch.setattr(catalog_mod, "asteroids_file", asteroids or ephemeris + ".missing")
    return catalog_mod.Catalog(Environment())


def test_missing_ephemeris_disables_planets(monkeypatch, stars, tmp_path, capsys):
    missing = str(tmp_path / "de440s.bsp")
    cat = make_catalog(monkeypatch, stars, missing)
    out = capsys.readouterr().out
    assert "de440s.bsp" in out and "not found" in out
    assert not cat.has_ephemeris
    assert cat.get_solar_system() == []
    assert cat.get_current_position("JUPITER") is None
    assert not os.path.exists(missing)  # never downloaded


def test_stars_work_without_ephemeris(monkeypatch, stars, tmp_path):
    cat = make_catalog(monkeypatch, stars, str(tmp_path / "none.bsp"))
    vega = (279.23, 38.78)
    nearby = cat.search_by_coordinate(*vega, radius=1.0, mag_limit=6)
    assert any("Vega" in str(t["Name"]) or t["Vmag"] < 0.5 for t in nearby)
    assert len(cat.get_bright_stars(3)) > 0


def test_corrupt_ephemeris_disables_planets(monkeypatch, stars, tmp_path, capsys):
    bad = tmp_path / "de440s.bsp"
    bad.write_bytes(b"garbage")
    cat = make_catalog(monkeypatch, stars, str(bad))
    assert not cat.has_ephemeris and "Could not load" in capsys.readouterr().out


@pytest.mark.requires_ephemeris
def test_planets_with_real_ephemeris(monkeypatch, stars):
    cat = make_catalog(monkeypatch, stars, os.path.join(ROOT, "data", "de440s.bsp"),
                       os.path.join(ROOT, "data", "sb441-n16.bsp"))
    assert cat.has_ephemeris
    jupiter = cat.get_current_position("JUPITER")
    assert 0 <= jupiter["RAdeg"] < 360 and -30 < jupiter["DEdeg"] < 30
    assert {"MOON", "SUN", "MARS"} <= set(cat.get_current_positions())  # all positions, visible or not
    for target in cat.get_solar_system():  # only what is above the horizon now
        assert target["is_planet"] and 0 <= target["RAdeg"] < 360
