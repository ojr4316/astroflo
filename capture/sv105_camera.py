"""
SVBONY SV105 imaging camera driver (UVC over V4L2).

Frames are read with OpenCV. Exposure/gain go through `v4l2-ctl` when installed (reliable
units, exposes exposure_dynamic_framerate), falling back to OpenCV properties otherwise.

Measured limits from `tools/sv105_probe.py` (data/sv105_limits.json) override the ranges the
driver reports, since UVC cameras often advertise exposures they cannot actually deliver.
"""
import json
import os
import time
from typing import Optional

import cv2
import numpy as np

from capture.imaging_camera import ImagingCamera, ImagingLimits
from capture import v4l2_util
from utils import BASE_DIR

LIMITS_FILE = os.path.join(BASE_DIR, "data", "sv105_limits.json")
DEFAULT_SIZE = (1920, 1080)
FLUSH_FRAMES = 2  # UVC applies new controls with a lag of a frame or two


def load_measured_limits(path: str = LIMITS_FILE) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


class SV105Camera(ImagingCamera):

    def __init__(self, limits_file: str = LIMITS_FILE):
        super().__init__()
        self.limits_file = limits_file
        self.device: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.ctrls = {}
        self.auto_ctrl = None
        self.exposure_ctrl = None
        self.use_v4l2_ctl = False
        self.fps_options = []
        self.current_fps = None

    # ---------- connection ----------
    def connect(self) -> bool:
        try:
            self.close()
            self.device = v4l2_util.find_device()
            if self.device is None:
                return False

            cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
            if not cap.isOpened():
                cap.release()
                return False
            self.cap = cap

            measured = load_measured_limits(self.limits_file)
            width, height = measured.get("width", DEFAULT_SIZE[0]), measured.get("height", DEFAULT_SIZE[1])
            fourcc = measured.get("fourcc", "YUYV")
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self._load_controls(measured, fourcc, width, height)
            self._enable_manual_exposure()
            self.configure(self.exposure_us, self.gain)

            ok, _ = cap.read()
            if not ok:
                self.close()
                return False
            print(f"SV105 connected on {self.device} ({width}x{height} {fourcc}), limits={self.limits}")
            return True
        except Exception as e:  # never let hot-plug errors escape
            print(f"SV105 connect failed: {e}")
            self.close()
            return False

    def _load_controls(self, measured: dict, fourcc: str, width: int, height: int):
        self.use_v4l2_ctl = v4l2_util.has_v4l2_ctl()
        reported = ImagingLimits()
        if self.use_v4l2_ctl:
            try:
                self.ctrls = v4l2_util.list_ctrls(self.device)
                self.auto_ctrl, self.exposure_ctrl = v4l2_util.exposure_ctrl_names(self.ctrls)
                if self.exposure_ctrl:
                    e = self.ctrls[self.exposure_ctrl]
                    reported.min_exposure_us = e.get("min", 1) * v4l2_util.UVC_EXPOSURE_UNIT_US
                    reported.max_exposure_us = e.get("max", 5000) * v4l2_util.UVC_EXPOSURE_UNIT_US
                if "gain" in self.ctrls:
                    reported.min_gain = self.ctrls["gain"].get("min", 0)
                    reported.max_gain = self.ctrls["gain"].get("max", 100)
                modes = v4l2_util.parse_frame_intervals(v4l2_util.run_v4l2_ctl(self.device, "--list-formats-ext"))
                for mode in modes:
                    if mode["fourcc"] == fourcc and mode["width"] == width and mode["height"] == height:
                        self.fps_options = sorted(mode["fps"])
            except Exception as e:
                print(f"SV105: v4l2-ctl unavailable/failed ({e}); using OpenCV controls")
                self.use_v4l2_ctl = False

        self.limits = ImagingLimits(
            min_exposure_us=measured.get("min_exposure_us", reported.min_exposure_us),
            max_exposure_us=measured.get("max_exposure_us", reported.max_exposure_us),
            min_gain=measured.get("min_gain", reported.min_gain),
            max_gain=measured.get("max_gain", reported.max_gain),
        )
        if "fps_options" in measured:
            self.fps_options = sorted(measured["fps_options"])

    def _enable_manual_exposure(self):
        if self.use_v4l2_ctl:
            values = {}
            if self.auto_ctrl:
                values[self.auto_ctrl] = 1  # UVC: 1 = Manual Mode
            if "exposure_dynamic_framerate" in self.ctrls:
                values["exposure_dynamic_framerate"] = 1  # let exposure exceed the frame interval
            if "white_balance_automatic" in self.ctrls:
                values["white_balance_automatic"] = 0
            elif "white_balance_temperature_auto" in self.ctrls:
                values["white_balance_temperature_auto"] = 0
            v4l2_util.set_ctrls(self.device, **values)
        else:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # V4L2 backend: 1 = manual

    def is_connected(self) -> bool:
        return self.cap is not None and self.device is not None and os.path.exists(self.device)

    def close(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None

    # ---------- settings ----------
    def _choose_fps(self, exposure_us: float):
        """ Highest supported frame rate whose frame interval fits the exposure. """
        if not self.fps_options:
            return None
        fitting = [f for f in self.fps_options if 1e6 / f >= exposure_us]
        return max(fitting) if fitting else min(self.fps_options)

    def configure(self, exposure_us: float, gain: float):
        exposure_us = self.limits.clamp_exposure(exposure_us)
        gain = self.limits.clamp_gain(gain)
        if self.cap is None:
            self.exposure_us, self.gain = exposure_us, gain
            return

        fps = self._choose_fps(exposure_us)
        if fps is not None and fps != self.current_fps:
            self.cap.set(cv2.CAP_PROP_FPS, fps)
            self.current_fps = fps

        if self.use_v4l2_ctl:
            values = {}
            if self.exposure_ctrl:
                values[self.exposure_ctrl] = max(1, round(exposure_us / v4l2_util.UVC_EXPOSURE_UNIT_US))
            if "gain" in self.ctrls:
                values["gain"] = round(gain)
            v4l2_util.set_ctrls(self.device, **values)
        else:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_us / v4l2_util.UVC_EXPOSURE_UNIT_US)
            self.cap.set(cv2.CAP_PROP_GAIN, gain)

        changed = (exposure_us != self.exposure_us) or (gain != self.gain)
        self.exposure_us, self.gain = exposure_us, gain
        if changed:
            self._flush()

    def _flush(self):
        for _ in range(FLUSH_FRAMES):
            if self.cap is None or not self.cap.grab():
                break

    # ---------- capture ----------
    def capture(self) -> Optional[np.ndarray]:
        if not self.is_connected():
            self.close()
            return None
        try:
            ok, frame = self.cap.read()
        except Exception:
            ok, frame = False, None
        if not ok or frame is None:
            self.close()
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


if __name__ == "__main__":
    cam = SV105Camera()
    if not cam.connect():
        raise SystemExit("SV105 not found")
    t = time.time()
    img = cam.capture()
    print("frame", None if img is None else img.shape, f"{time.time() - t:.2f}s")
    cam.close()
