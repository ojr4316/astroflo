from abc import ABC, abstractmethod
import os
import cv2
import datetime
import threading

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
    
    @abstractmethod
    def configure(self, exposure: int = 1_000_000, gain: float = 16.0):
        self.exposure = exposure
        self.gain = gain

    @abstractmethod
    def capture(self):
       pass
    
    @abstractmethod
    def stop(self):
        self.running = False

    def save_frame(self, frame):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.save_dir, 
            f"{timestamp}.jpg"
        )
        cv2.imwrite(filename, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        return filename
 