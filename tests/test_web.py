""" Web control API tests — run with: pytest tests/test_web.py """
import os
import sys
import time
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient

from capture.capture_store import CaptureStore
from capture.imaging_camera import ImagingController
from config import SettingsStore
from hardware.state import ScreenState
from observation_context import ObservationContext
from web.server import Services, create_app


class StubCatalog:
    def __init__(self):
        self.setup_calls = 0

    def setup(self):
        self.setup_calls += 1

    def get_bright_stars(self, mag):
        return [{"Name": "Vega", "RAdeg": 279.23, "DEdeg": 38.78, "Vmag": 0.03, "is_planet": False},
                {"Name": "Arcturus", "RAdeg": 213.92, "DEdeg": 19.18, "Vmag": -0.05, "is_planet": False}]

    def get_dsos(self, mag):
        return [{"Name": "M31", "RAdeg": 10.68, "DEdeg": 41.27, "Vmag": 3.4, "is_planet": False}]

    def get_solar_system(self):
        return [{"Name": "JUPITER", "RAdeg": 100.0, "DEdeg": 22.0, "Vmag": -2.5, "is_planet": True}]


class StubUI:
    def __init__(self):
        class SM: state = ScreenState.MAIN_MENU
        self.state_manager = SM()
        self.display_enabled = True
        self.brightness = 0.5

    def set_display(self, enabled=None, brightness=None):
        if enabled is not None:
            self.display_enabled = enabled
        if brightness is not None:
            self.brightness = brightness

    def set_screen(self, state):
        self.state_manager.state = state


@pytest.fixture
def env(tmp_path):
    settings = SettingsStore(str(tmp_path / "settings.json"), legacy_path=None)
    store = CaptureStore(str(tmp_path / "captures"), max_kept=3)
    ctx = ObservationContext()
    ctx.solver_state.save_offset = lambda off: setattr(ctx.solver_state, "target_pixel", off)  # don't touch offset.npy
    imaging = ImagingController(lambda img, meta: store.save(img, "imaging", meta, save_fits=True))
    svc = Services(ctx=ctx, settings=settings, store=store, imaging=imaging, catalog=StubCatalog(), ui=StubUI())
    client = TestClient(create_app(svc))
    yield client, svc
    imaging.disconnect()


def test_index_and_state(env):
    client, svc = env
    assert "ASTROFLO" in client.get("/").text
    s = client.get("/api/state").json()
    assert s["solved"] is False and s["position"] is None
    svc.ctx.telescope_state.position = (279.0, 38.0)
    s = client.get("/api/state").json()
    assert s["position"]["ra"] == 279.0 and "alt" in s["position"]


def test_targets_and_guidance(env):
    client, svc = env
    r = client.get("/api/targets", params={"type": "stars", "q": "veg"}).json()
    assert [t["name"] for t in r["items"]] == ["Vega"]
    assert client.post("/api/target", json={"name": "m31"}).json()["name"] == "M31"
    assert client.post("/api/target", json={"name": "nope"}).status_code == 404
    svc.ctx.telescope_state.position = (10.0, 40.0)
    t = client.post("/api/target", json={"ra": 10.68, "dec": 41.27}).json()
    assert t["distance_deg"] > 0 and t["north_deg"] > 0
    assert client.post("/api/target", json={"ra": 400, "dec": 0}).status_code == 422
    client.delete("/api/target")
    assert client.get("/api/state").json()["target"] is None


def test_finder_capture_ring_buffer(env):
    client, svc = env
    assert client.post("/api/finder/capture").status_code == 409
    svc.ctx.camera_state.latest_image = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    assert client.get("/api/finder/frame.jpg").headers["content-type"] == "image/jpeg"
    ids = []
    for _ in range(5):
        ids.append(client.post("/api/finder/capture").json()["id"])
        time.sleep(0.002)
    items = client.get("/api/captures").json()["items"]
    assert len(items) == 3 and items[0]["id"] == ids[-1]  # newest kept only
    assert client.get(f"/api/captures/{ids[0]}").status_code == 404
    assert client.get(f"/api/captures/{ids[-1]}/image.jpg").status_code == 200
    assert client.get("/api/captures/..%2Fsettings/image.jpg").status_code == 404
    assert client.delete(f"/api/captures/{ids[-1]}").status_code == 200


def test_imaging_camera(env):
    client, svc = env
    assert client.post("/api/imaging/connect").status_code == 502  # backend 'none'
    client.put("/api/settings", json={"imaging_camera": {"backend": "fake"}})
    assert client.post("/api/imaging/connect").json()["connected"] is True
    st = client.post("/api/imaging/expose", json={"exposure_s": 0.1, "count": 2}).json()
    assert st["exposing"] is True
    assert client.post("/api/imaging/expose", json={"exposure_s": 0.1}).status_code == 409
    for _ in range(100):
        if not client.get("/api/imaging").json()["status"]["exposing"]:
            break
        time.sleep(0.05)
    items = client.get("/api/captures", params={"source": "imaging"}).json()["items"]
    assert len(items) == 2 and items[0]["fits"] is True and items[0]["exposure_s"] == 0.1
    assert client.get(f"/api/captures/{items[0]['id']}/image.fits").status_code == 200
    assert client.get("/api/imaging/frame.jpg").status_code == 200
    # loop + abort
    client.post("/api/imaging/expose", json={"exposure_s": 0.1, "loop": True, "save": False})
    client.post("/api/imaging/abort")
    svc.imaging.thread.join(2)
    assert client.get("/api/imaging").json()["status"]["exposing"] is False


def test_settings_apply_and_persist(env):
    client, svc = env
    r = client.put("/api/settings", json={"optics": {"eyepiece": 10}, "location": {"latitude": 51.5}, "captures": {"max_kept": 2}})
    assert r.status_code == 200 and r.json()["optics"]["eyepiece"] == 10
    assert svc.ctx.telescope_optics.eyepiece == 10
    assert abs(svc.ctx.environment.astropy_location.lat.deg - 51.5) < 1e-6
    assert svc.catalog.setup_calls == 1 and svc.store.max_kept == 2
    assert client.put("/api/settings", json={"optics": {"eyepiece": -1}}).status_code == 422
    assert SettingsStore(svc.settings.path, None).settings.optics.eyepiece == 10
    assert "properties" in client.get("/api/settings/schema").json()


def test_display_and_alignment(env):
    client, svc = env
    d = client.put("/api/display", json={"enabled": False, "brightness": 0.2}).json()
    assert d["enabled"] is False and svc.ui.brightness == 0.2
    assert svc.settings.settings.display.enabled is False
    assert client.put("/api/display", json={"screen": "BOGUS"}).status_code == 422
    assert client.post("/api/alignment", json={"row": 100, "col": 200}).status_code == 200
    assert list(svc.ctx.solver_state.target_pixel) == [100, 200]


def test_legacy_settings_migration(tmp_path):
    legacy = tmp_path / "settings.txt"
    legacy.write_text("aperture: 150\nfocal_length: 750\nx_offset: 1.5\n")
    s = SettingsStore(str(tmp_path / "settings.json"), str(legacy)).settings
    assert s.optics.aperture == 150 and s.optics.focal_length == 750 and s.alignment.x_offset == 1.5
