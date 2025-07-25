from abc import ABC, abstractmethod
import os
import cv2
import datetime
import threading
from enum import Enum

class GainProfile(Enum):
    HIGH=16.0
    MID=8.0
    LOW=2.0

class ExposureProfile(Enum):
    FAST=300_000
    DEFAULT=600_000
    LONG=1_500_000
    STACK=10_000_000

class Camera(ABC):

    def __init__(self, save_dir: str = "captures"):
        self.save_dir = save_dir

        self.running = False
        self.lock = threading.Lock()

        self.save = False
        os.makedirs(self.save_dir, exist_ok=True)

        self.exposure = 1_000_000 #us
        self.gain = 1.0

        self.last_metadata = None

    @abstractmethod
    def start(self):
        self.running = True
        self.configure(ExposureProfile.DEFAULT.value, GainProfile.HIGH.value)
    
    @abstractmethod
    def configure(self, exposure: int = 1_000_000, gain: float = 8.0):
        self.exposure = exposure
        self.gain = gain

    @abstractmethod
    def capture(self):
        if not self.running:
            raise RuntimeError("Camera is not running. Please start the camera before capturing.")
    
    @abstractmethod
    def stop(self):
        self.running = False

    def save_frame(self, frame):
        #return "/home/owen/astroflo/captures/20250525_002707.jpg"

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.save_dir, 
            "test.jpg"#f"{timestamp}.jpg"
        )
        cv2.imwrite(filename, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        return filename
 