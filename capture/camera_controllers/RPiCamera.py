from picamera2 import Picamera2
import threading
import time
import datetime
import os
import cv2

class RPiCamera:
    def __init__(self, save_dir="captures"):
        self.picam2 = Picamera2()
        self.config = self.picam2.create_still_configuration(
            main={"size": (4056, 3040)}
        )
        self.picam2.configure(self.config)
 
        # Threading and synchronization
        self.running = False
        self.lock = threading.Lock()
 
        # Image processing and storage
        self.save_dir = save_dir
        self.save = False
        os.makedirs(self.save_dir, exist_ok=True)
 
        # Status tracking
        self.current_params = {
            "exposure_time": 1.0,
            "gain": 1.0,
            "binning": 1
        }
        self.last_metadata = None
 
    def start(self):
        self.picam2.set_controls({
            "AeEnable": False,
            "AwbEnable": False,
        })
        self.picam2.start()
        print("Warming up camera...")
        time.sleep(2) 
        self.running = True
        print("Camera controller started!")
 
    def capture(self, exposure_time, gain, binning=1):
        if self.last_metadata == None:
            self._apply_settings(exposure_time, gain, binning)
        else:
            last_exp = self.last_metadata.get("ExposureTime", 0) / 1e6
            last_gain = self.last_metadata.get("AnalogueGain", 0)
            if last_exp != exposure_time or gain != last_gain:
                self._apply_settings(exposure_time, gain, binning)
 
        actual_exp = 0
        actual_gain = 0
        while actual_exp != exposure_time and gain != actual_gain:
            print(f"exp{exposure_time}s {gain}")
            frame = self.picam2.capture_array()
    
            # Get metadata for verification
            metadata = self.picam2.capture_metadata()
            self.last_metadata = metadata
    
            actual_exp = metadata.get("ExposureTime", 0) / 1e6
            actual_gain = metadata.get("AnalogueGain", 0)
 
        if self.save:
            self._save_frame(frame, self.current_params)
 
        return frame
 
    def _apply_settings(self, exposure_time, gain, binning=1):
        us = int(exposure_time * 1e6)
 
        self.picam2.set_controls({"FrameDurationLimits": (us, 1000000000)})
        time.sleep(0.1) 

        controls_dict = {
            "AeEnable": False,
            "AwbEnable": False,
            "ExposureTime": us,
            "AnalogueGain": float(gain)
        }
        self.picam2.set_controls(controls_dict)
 
        wait_time = max(0.5, exposure_time * 0.5)
        print(f"Waiting {wait_time:.1f}s for settings to apply...")
        time.sleep(wait_time)
 
        _ = self.picam2.capture_array()
 
        self.current_params = {
            "exposure_time": exposure_time,
            "gain": gain,
            "binning": binning
        }
 
    def _save_frame(self, frame, params):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        exp_ms = int(params["exposure_time"] * 1000)
        filename = os.path.join(
            self.save_dir, 
            f"{timestamp}.jpg"
        )
        cv2.imwrite(filename, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
 
    def stop(self):
        self.running = False
        self.picam2.stop()
        print("Camera controller stopped!")
 
 