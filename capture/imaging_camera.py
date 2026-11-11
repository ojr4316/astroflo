""" Interface for the imaging (non plate-solving) camera, e.g. the SVBONY SV105. """
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class ImagingLimits:
    min_exposure_us: float = 100.0
    max_exposure_us: float = 500_000.0
    min_gain: float = 0.0
    max_gain: float = 100.0

    def clamp_exposure(self, exposure_us: float) -> float:
        return float(min(self.max_exposure_us, max(self.min_exposure_us, exposure_us)))

    def clamp_gain(self, gain: float) -> float:
        return float(min(self.max_gain, max(self.min_gain, gain)))


class ImagingCamera(ABC):
    """ Only the imaging controller thread may call these methods. """

    def __init__(self):
        self.limits = ImagingLimits()
        self.exposure_us = 10_000.0
        self.gain = 0.0

    @abstractmethod
    def connect(self) -> bool:
        """ Try to open the camera. Returns True when connected. Must not raise. """

    @abstractmethod
    def is_connected(self) -> bool:
        """ Cheap check that the camera is still present. """

    @abstractmethod
    def configure(self, exposure_us: float, gain: float):
        """ Apply exposure (microseconds) and gain, clamped to self.limits. """

    @abstractmethod
    def capture(self) -> Optional[np.ndarray]:
        """ Return one RGB frame, or None if the camera failed/disconnected. """

    @abstractmethod
    def close(self):
        """ Release the device. Safe to call when not connected. """
