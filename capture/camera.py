from abc import ABC, abstractmethod
import os
import cv2
import datetime
import threading
from enum import Enum
from observation_context import CameraState
from queue import Queue
from utils import BASE_DIR

import time

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

    def __init__(self, camera_state: CameraState):
        self.camera_state = camera_state
        self.save_dir = os.path.join(BASE_DIR, "captures")

        self.running = False
        self.lock = threading.Lock()

        self.save = False
        os.makedirs(self.save_dir, exist_ok=True)

        self.last_metadata = None
        self.queue = Queue()

    @abstractmethod
    def start(self):
        self.running = True
        self.configure(ExposureProfile.DEFAULT.value, GainProfile.HIGH.value)
    
    @abstractmethod
    def configure(self, exposure: int = 1_000_000, gain: float = 8.0):
        self.camera_state.exposure = exposure
        self.camera_state.gain = gain

    @abstractmethod
    def capture(self):
        if not self.running:
            raise RuntimeError("Camera is not running. Please start the camera before capturing.")
    
    @abstractmethod
    def stop(self):
        self.running = False

    def save_frame(self, frame):
        filename = os.path.join(
            self.save_dir, 
            "latest.jpg"#f"{timestamp}.jpg"
        )
        cv2.imwrite(filename, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        return filename
 
    def capturer(self): # Run in a separate thread to continuously capture images
        self.start()
        while self.running:
            img = self.capture() # Adds new image to the queue to be processed by the solver/analyzer
            self.camera_state.latest_image = img
            time.sleep(0.01)
        self.stop()