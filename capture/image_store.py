""" Writes imaging camera frames to saves/<target>/<timestamp>.png """
import os
import re
import datetime
from typing import Optional

import cv2
import numpy as np

from utils import BASE_DIR

MANUAL_DIR = "manual"
DEFAULT_SAVE_DIR = os.path.join(BASE_DIR, "saves")
EXTENSION = ".png"


def sanitize(name: Optional[str]) -> str:
    """ Filesystem-safe directory name for a target. """
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", (name or "").strip())
    cleaned = cleaned.strip(" .")
    return cleaned or "unnamed"


def timestamp_name(now: datetime.datetime) -> str:
    return now.strftime("%Y-%m-%d_%H-%M-%S-") + f"{now.microsecond // 1000:03d}"


class ImageStore:
    def __init__(self, base_dir: str = DEFAULT_SAVE_DIR):
        self.base_dir = base_dir

    def directory_for(self, target: Optional[str]) -> str:
        """ target=None means a manual capture. """
        sub = MANUAL_DIR if target is None else sanitize(target)
        return os.path.join(self.base_dir, sub)

    def path_for(self, target: Optional[str], now: Optional[datetime.datetime] = None) -> str:
        now = now or datetime.datetime.now()
        directory = self.directory_for(target)
        os.makedirs(directory, exist_ok=True)

        stem = timestamp_name(now)
        path = os.path.join(directory, stem + EXTENSION)
        n = 1
        while os.path.exists(path):
            path = os.path.join(directory, f"{stem}_{n}{EXTENSION}")
            n += 1
        return path

    def save(self, frame: np.ndarray, target: Optional[str], now: Optional[datetime.datetime] = None) -> str:
        """ Save an RGB (or grayscale) frame losslessly. Returns the written path. Raises IOError on failure. """
        path = self.path_for(target, now)
        if frame.ndim == 3 and frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        if not cv2.imwrite(path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 1]):
            raise IOError(f"Failed to write {path}")
        return path
