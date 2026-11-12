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

    def __init__(self, scene_brightness: float = 2_000.0, size=(120, 160), simulate_exposure_time: bool = False,
                 source: Optional[str] = None, reference_exposure_s: float = 0.1, seed: Optional[int] = None):
        """
        source: optional image file/folder. Each image is treated as the scene at `reference_exposure_s`
        and gain 0; frames are scaled by exposure and gain like the synthetic scene.
        """
        super().__init__()
        self.rng = np.random.default_rng(seed)
        self.reference_exposure_s = reference_exposure_s
        self.images = []
        self._image_idx = 0
        if source:
            from capture.fake_camera import list_images, load_rgb
            for path in list_images(source):
                img = load_rgb(path)
                if img is not None:
                    self.images.append(img.astype(np.float32).mean(axis=-1))
            if not self.images:
                print(f"Fake imaging camera: no readable images in '{source}', using synthetic frames")
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
        if self.images:
            scene = self.images[self._image_idx % len(self.images)]
            self._image_idx += 1
            level = scene * (self.exposure_us / 1e6) / self.reference_exposure_s * gain_factor
            noise = self.rng.normal(0, 2, scene.shape)
        else:
            level = self.scene_brightness * (self.exposure_us / 1e6) * gain_factor
            noise = self.rng.normal(0, 2, self.size)
        frame = np.clip(level + noise, 0, 255).astype(np.uint8)
        self.frames_captured += 1
        return np.stack([frame] * 3, axis=-1)

    def close(self):
        self._open = False
