""" Run the web UI off-Pi with simulated cameras/solver: python -m web.dev_server
Uses the real Catalog if data files are present, otherwise a small built-in list. """
import os
import threading
import time
import numpy as np
from PIL import Image
import uvicorn

from capture.capture_store import CaptureStore
from capture.remote_imaging import ImagingController
from config import SettingsStore
from observation_context import ObservationContext
from utils import BASE_DIR
from web.server import Services, create_app


class DemoCatalog:
    stars = [("Vega", 279.234, 38.784, 0.03), ("Arcturus", 213.915, 19.182, -0.05), ("Deneb", 310.358, 45.280, 1.25),
             ("Altair", 297.696, 8.868, 0.77), ("Polaris", 37.954, 89.264, 1.98)]
    dsos = [("M31", 10.685, 41.269, 3.4), ("M13", 250.423, 36.461, 5.8), ("M57", 283.396, 33.029, 8.8)]

    def setup(self): pass
    def _l(self, rows, mag): return [{"Name": n, "RAdeg": r, "DEdeg": d, "Vmag": m} for n, r, d, m in rows if m <= mag]
    def get_bright_stars(self, mag): return self._l(self.stars, mag)
    def get_dsos(self, mag): return self._l(self.dsos, mag)
    def get_solar_system(self): return [{"Name": "JUPITER", "RAdeg": 95.0, "DEdeg": 23.0, "Vmag": -2.5, "is_planet": True}]


class DemoUI:
    def __init__(self):
        from hardware.state import ScreenState
        class SM: state = ScreenState.MAIN_MENU
        self.state_manager, self.display_enabled, self.brightness = SM(), True, 0.5
    def set_display(self, enabled=None, brightness=None):
        if enabled is not None: self.display_enabled = enabled
        if brightness is not None: self.brightness = brightness
    def set_screen(self, state): self.state_manager.state = state


def main():
    settings = SettingsStore(os.path.join(BASE_DIR, "captures", "dev_settings.json"), legacy_path=None)
    if settings.settings.imaging_camera.backend == "none":
        settings.update({"imaging_camera": {"backend": "fake"}})
    ctx = ObservationContext()
    ctx.apply_settings(settings.settings)
    store = CaptureStore(os.path.join(BASE_DIR, "captures", "dev_store"), settings.settings.captures.max_kept)
    imaging = ImagingController(lambda img, meta: store.save(img, "imaging", meta, save_fits=True))

    frame = np.array(Image.open(os.path.join(BASE_DIR, "test_data", "out_of_focus.jpg")).convert("RGB"))
    ctx.camera_state.latest_image = frame
    ctx.target_state.set_target(279.234, 38.784, "Vega")

    def sim():  # wander the "telescope" toward the target
        ra, dec = 270.0, 30.0
        while True:
            ra += (279.234 - ra) * 0.01; dec += (38.784 - dec) * 0.01
            ctx.telescope_state.position = (ra, dec)
            ctx.solver_state.last_solved = time.time()
            time.sleep(0.5)
    threading.Thread(target=sim, daemon=True).start()

    svc = Services(ctx=ctx, settings=settings, store=store, imaging=imaging, catalog=DemoCatalog(), ui=DemoUI())
    uvicorn.run(create_app(svc), host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


if __name__ == "__main__":
    main()
