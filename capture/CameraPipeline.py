import cv2
import numpy as np

class CameraPipeline:
    def __init__(self, camera):
        self.camera = camera
        self.camera.start()
        self.configure()
 
    def configure(self, exposure=1_000_000, gain=1.0):
        self.exposure = exposure
        self.gain = gain
        self.camera.configure(exposure, gain)

    def capture(self):
        frame = self.camera.capture()
        return frame
        #processed_frame = self._process_frame(frame)
        #return processed_frame
 
    def _process_frame(self, frame):
        resized = cv2.resize(frame, (224, 224)) # Resize to MobileNetV3 input

        return resized
 
    def shutdown(self):
        self.camera.stop()
 