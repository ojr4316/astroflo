from abc import ABC, abstractmethod
import os
import cv2
import datetime

class Camera(ABC):

    def __init__(self, save_dir: str = "captures"):
        self.save_dir = save_dir

        self.running = False
        self.save = False
        os.makedirs(self.save_dir, exist_ok=True)

        self.exposure = 1_000_000 #us
        self.gain = 1.0
        self.binning = 1
        
        self.current_params = {
            "exposure": 1_000_000,
            "gain": 1.0,
            "binning": 1
        }

        self.last_metadata = None

    @abstractmethod
    def start(self):
        self.running = True
    
    @abstractmethod
    def capture(self, exposure: int = 1_000_000, gain: float = 1.0, binning: int = 1):
        self.current_params["exposure"] = exposure
        self.current_params["gain"] = gain
        self.current_params["binning"] = binning

    @abstractmethod
    def stop(self):
        self.running = False

    def save_frame(self, frame, params):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        exp_ms = int(params["exposure_time"] * 1000)
        filename = os.path.join(
            self.save_dir, 
            f"{timestamp}.jpg"
        )
        cv2.imwrite(filename, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
 