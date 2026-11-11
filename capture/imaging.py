""" Imaging controller: owns the imaging camera and runs auto/manual capture on its own thread. """
import math
import time
from typing import Optional

from capture.imaging_camera import ImagingCamera
from capture.image_store import ImageStore
from capture.auto_exposure import next_settings
from observation_context import ObservationContext, TelescopeOptics
from utils import haversine_dist

# SV105 (Sony IMX307): 1920x1080 at 2.9 um
SENSOR_WIDTH_MM = 1920 * 0.0029
SENSOR_HEIGHT_MM = 1080 * 0.0029

MAX_SOLVE_AGE_S = 10.0
RECONNECT_INTERVAL_S = 2.0
IDLE_SLEEP_S = 0.1
START_EXPOSURE_US = 10_000.0


def imaging_field_radius(optics: TelescopeOptics, margin: float = 1.0) -> float:
    """ Half of the diagonal field of view of the imaging sensor, in degrees. """
    diagonal_mm = math.hypot(SENSOR_WIDTH_MM, SENSOR_HEIGHT_MM)
    fov_deg = math.degrees(2 * math.atan(diagonal_mm / (2 * optics.focal_length)))
    return fov_deg / 2 * margin


def target_in_field(ctx: ObservationContext, now: Optional[float] = None, margin: float = 1.0) -> bool:
    now = time.time() if now is None else now
    target = ctx.target_state
    position = ctx.telescope_state.position
    if not target.has_target() or position is None:
        return False
    if now - ctx.solver_state.last_solved > MAX_SOLVE_AGE_S:
        return False
    dist_deg = math.degrees(haversine_dist(position[0], position[1], target.ra, target.dec))
    return dist_deg <= imaging_field_radius(ctx.telescope_optics, margin)


class ImagingController:

    def __init__(self, camera: ImagingCamera, ctx: ObservationContext, store: Optional[ImageStore] = None,
                 reconnect_interval: float = RECONNECT_INTERVAL_S, idle_sleep: float = IDLE_SLEEP_S):
        self.camera = camera
        self.ctx = ctx
        self.state = ctx.imaging_state
        self.store = store or ImageStore()
        self.reconnect_interval = reconnect_interval
        self.idle_sleep = idle_sleep
        self.last_connect_attempt = 0.0
        self.running = False

        self.camera.configure(max(START_EXPOSURE_US, camera.limits.min_exposure_us), camera.limits.min_gain)
        self._publish_settings()

    def _publish_settings(self):
        self.state.exposure_us = self.camera.exposure_us
        self.state.gain = self.camera.gain

    def _set_disconnected(self):
        self.camera.close()
        self.state.connected = False

    def _ensure_connected(self) -> bool:
        if self.state.connected and self.camera.is_connected():
            return True
        if self.state.connected:
            print("Imaging camera disconnected")
            self._set_disconnected()
        now = time.monotonic()
        if now - self.last_connect_attempt >= self.reconnect_interval:
            self.last_connect_attempt = now
            if self.camera.connect():
                print("Imaging camera connected")
                self.state.connected = True
                self._publish_settings()
        return self.state.connected

    def _capture_and_save(self, target: Optional[str]) -> bool:
        frame = self.camera.capture()
        if frame is None:
            self._set_disconnected()
            self.state.set_result("Failed")
            return False
        try:
            self.store.save(frame, target)
        except (IOError, OSError) as e:
            print(f"Imaging save failed: {e}")
            self.state.auto_enabled = False  # e.g. disk full: stop instead of spinning
            self.state.set_result("Save failed")
            return False
        self.state.frames_saved += 1
        if target is not None:  # auto mode adapts settings; manual uses them as-is
            exposure, gain = next_settings(frame, self.camera.exposure_us, self.camera.gain, self.camera.limits)
            if (exposure, gain) != (self.camera.exposure_us, self.camera.gain):
                self.camera.configure(exposure, gain)
                self._publish_settings()
        return True

    def step(self) -> bool:
        """ One iteration. Returns True if a frame was captured (caller should not sleep). """
        connected = self._ensure_connected()
        self.state.target_in_field = target_in_field(self.ctx)

        if self.state.manual_requested.is_set():
            self.state.manual_requested.clear()
            if not connected:
                self.state.set_result("Failed")
                return False
            ok = self._capture_and_save(None)
            if ok:
                self.state.set_result("Saved")
            return ok

        if connected and self.state.auto_enabled and self.state.target_in_field:
            name = self.ctx.target_state.name or "unnamed"
            return self._capture_and_save(name)

        return False

    def run(self):
        self.running = True
        while self.running:
            try:
                captured = self.step()
            except Exception as e:  # keep the thread alive across driver errors
                print(f"Imaging error: {e}")
                self._set_disconnected()
                captured = False
            if not captured:
                time.sleep(self.idle_sleep)

    def stop(self):
        self.running = False
