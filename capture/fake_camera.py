""" Simulated finder (plate-solving) camera that replays test images. Runs on any OS. """
import os
import time
from typing import List, Optional, Sequence, Union

import numpy as np
from PIL import Image

from capture.camera import Camera
from observation_context import CameraState

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")


def list_images(source: str) -> List[str]:
    """ Image files for a file or folder source, in file-name order """
    if source and os.path.isfile(source):
        return [source]
    if source and os.path.isdir(source):
        return [os.path.join(source, f) for f in sorted(os.listdir(source))
                if f.lower().endswith(IMAGE_EXTENSIONS) and os.path.isfile(os.path.join(source, f))]
    return []


def load_rgb(path: str) -> Optional[np.ndarray]:
    try:
        with Image.open(path) as img:
            return np.array(img.convert("RGB"), dtype=np.uint8)
    except (OSError, ValueError) as e:
        print(f"Simulated camera: skipping unreadable image {path} ({e})")
        return None


class ImageFolderCamera(Camera):
    """
    Replays images from a file or folder (name order, looping). Frames are RGB uint8 arrays,
    like the Pi camera's. Falls back to random noise when no readable image is found.
    """

    def __init__(self, camera_state: CameraState, source: Union[str, Sequence[np.ndarray], None] = None,
                 loop: bool = True, simulate_exposure: bool = True, noise_size=(256, 256)):
        super().__init__(camera_state)
        self.loop = loop
        self.simulate_exposure = simulate_exposure
        self.noise_size = noise_size
        self.fake_idx = 0
        self._cache = {}
        if isinstance(source, (list, tuple)):  # in-memory frames
            self.paths = list(range(len(source)))
            self._cache = {i: np.asarray(f) for i, f in enumerate(source)}
        else:
            self.paths = list_images(source) if source else []
            if source and not self.paths:
                print(f"Simulated camera: no readable images in '{source}', using random noise frames")

    def start(self):
        super().start()
        print(f"Simulated finder camera started ({len(self.paths)} image(s))")

    def stop(self):
        super().stop()

    def configure(self, exposure: int = 1_000_000, gain: float = 1.0):
        super().configure(exposure, gain)

    def _noise(self) -> np.ndarray:
        h, w = self.noise_size
        return np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)

    def _frame(self, key) -> Optional[np.ndarray]:
        if key not in self._cache:
            self._cache[key] = load_rgb(key)
        return self._cache[key]

    def next_frame(self) -> np.ndarray:
        """ Next image without the exposure wait (noise if none are readable) """
        for _ in range(len(self.paths)):
            if self.fake_idx >= len(self.paths):
                if not self.loop:
                    break
                self.fake_idx = 0
            key = self.paths[self.fake_idx]
            self.fake_idx += 1
            frame = self._frame(key)
            if frame is not None:
                return frame
        return self._noise()

    def capture(self):
        super().capture()
        if self.simulate_exposure:
            time.sleep(self.camera_state.exposure / 1e6)
        return self.next_frame()  # capturer() queues it


class FakeCamera(ImageFolderCamera):
    """ Backwards-compatible name: FakeCamera(camera_state, [frames]) """

    def __init__(self, camera_state: CameraState, fake_feed=None):
        super().__init__(camera_state, list(fake_feed) if fake_feed else None)
