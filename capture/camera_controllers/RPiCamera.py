from camera_controllers.Camera import Camera
import time
import datetime
import os
import cv2
from picamera2 import Picamera2

class RPiCamera(Camera):
    def __init__(self, save_dir="captures"):
        super().__init__(save_dir=save_dir)

        self.picam2 = Picamera2()
        self.config = self.picam2.create_still_configuration(
            main={"size": (4056, 3040)}
        )
        self.picam2.configure(self.config)
 
    def start(self):
        self.picam2.set_controls({
            "AeEnable": False,
            "AwbEnable": False,
        })
        self.picam2.start()
        print("Warming up camera...")
        time.sleep(2) 
        self.running = True
        super().start()
        print("Camera controller started!")
 
    def capture(self):
        super().capture()
        
        frame = self.picam2.capture_array()
        self.last_metadata = self.picam2.capture_metadata()
        if self.save:
            self.save_frame(frame, self.current_params)
 
        return frame
 

    def configure(self, goal_exposure, goal_gain, max_attempts=10):
        super().configure(goal_exposure, goal_gain)
        self.picam2.set_controls({
            "AeEnable": False,
            "AwbEnable": False,
            "ExposureTime": int(goal_exposure),
            "AnalogueGain": float(goal_gain)
        })
        time.sleep(0.1) # Apply delay

        if self.last_metadata is None:
            _ = self.picam2.capture_array()
            self.last_metadata = self.picam2.capture_metadata()

        actual_exp = self.last_metadata.get("ExposureTime", 0)
        actual_gain = self.last_metadata.get("AnalogueGain", 0)

        attempts = 0
        while (abs(goal_exposure-actual_exp) > 10 or abs(goal_gain-actual_gain) > 0.1) and attempts < max_attempts:
            self.picam2.set_controls({
                "ExposureTime": int(goal_exposure),
                "AnalogueGain": float(goal_gain)
            })
            
            time.sleep(0.2)  # Wait longer between attempts
            _ = self.picam2.capture_array()  # capture test frame
            self.last_metadata = self.picam2.capture_metadata()
    
            actual_exp = self.last_metadata.get("ExposureTime", 0)
            actual_gain = self.last_metadata.get("AnalogueGain", 0)
            print(f"Attempt {attempts + 1}: Actual Exposure: {actual_exp}/{goal_exposure}, Actual Gain: {actual_gain}/{goal_gain}")
            attempts += 1
 
    def stop(self):
        super().stop()
        self.picam2.stop()
        print("Camera controller stopped!")
 
 