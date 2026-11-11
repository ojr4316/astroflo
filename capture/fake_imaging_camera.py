""" Fake imaging camera for development machines and tests. """
import time
from typing import Optional

import numpy as np

from capture.imaging_camera import ImagingCamera, ImagingLimits


class FakeImagingCamera(ImagingCamera):
    """
    Simulates a scene: pixel value ~= scene_brightness * exposure_s * gain_factor.
    `present` can be toggled to simulate unplugging the camera.
    """

    def __init__(self, scene_brightness: float = 2_000.0, size=(120, 160), simulate_exposure_time: bool = False):
        super().__init__()
        self.limits = ImagingLimits(min_exposure_us=32, max_exposure_us=1_000_000, min_gain=0, max_gain=100)
        self.scene_brightness = scene_brightness  # pixel value per second of exposure at gain 0
        self.size = size
        self.simulate_exposure_time = simulate_exposure_time
        self.present = True
        self._open = False
        self.frames_captured = 0

    def connect(self) -> bool:
        self._open = self.present
        return self._open

    def is_connected(self) -> bool:
        if not self.present:
            self._open = False
        return self._open

    def configure(self, exposure_us: float, gain: float):
        self.exposure_us = self.limits.clamp_exposure(exposure_us)
        self.gain = self.limits.clamp_gain(gain)

    def capture(self) -> Optional[np.ndarray]:
        if not self.is_connected():
            return None
        if self.simulate_exposure_time:
            time.sleep(self.exposure_us / 1e6)
        gain_factor = 10 ** (self.gain / 50.0)  # 0..100 -> 1x..100x
        level = self.scene_brightness * (self.exposure_us / 1e6) * gain_factor
        noise = np.random.normal(0, 2, self.size)
        frame = np.clip(level + noise, 0, 255).astype(np.uint8)
        self.frames_captured += 1
        return np.stack([frame] * 3, axis=-1)

    def close(self):
        self._open = False
