from capture.camera import Camera
import time
from picamera2 import Picamera2
from operation import OperationManager
from PIL import Image
import numpy as np

square = (512, 512)
low_res = (640, 480)
high_res = (4056, 3040)

class RPiCamera(Camera):
    def __init__(self, save_dir="captures"):
        super().__init__(save_dir=save_dir)

        self.picam2 = Picamera2()
        self.config = self.picam2.create_still_configuration(
            main={"size": square}
        )
        self.picam2.configure(self.config)
 
    def start(self):
        self.picam2.start()
        super().start()
        print("Camera controller started!")
 
    def capture(self):
        super().capture()
        
        frame = self.picam2.capture_array()
        self.last_metadata = self.picam2.capture_metadata()            

        if not OperationManager.use_real_images:
            return np.array(Image.open("./test_data/vega_focus.jpg"))
        if OperationManager.save_over:
            self.save_frame(frame)
        return frame

    def configure(self, goal_exposure, goal_gain=2, max_attempts=10):
        super().configure(goal_exposure, goal_gain)

        currently_on = self.running
        if not currently_on:
            self.picam2.start()

        self.picam2.set_controls({
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
        while (abs(goal_exposure-actual_exp) > 1000 or abs(goal_gain-actual_gain) > 0.1) and attempts < max_attempts:
            self.picam2.set_controls({
                "ExposureTime": int(goal_exposure),
                "AnalogueGain": float(goal_gain)
            })
            
            time.sleep(0.1)
            _ = self.picam2.capture_array()
            self.last_metadata = self.picam2.capture_metadata()
    
            actual_exp = self.last_metadata.get("ExposureTime", 0)
            actual_gain = self.last_metadata.get("AnalogueGain", 0)
            print(f"Attempt {attempts + 1}: Actual Exposure: {actual_exp}/{goal_exposure}, Actual Gain: {actual_gain}/{goal_gain}")
            attempts += 1
        if not currently_on:
            self.picam2.stop()
        
    def stop(self):
        super().stop()
        self.picam2.stop()
        print("Camera controller stopped!")
 
 