import cv2
import numpy as np

# TODO: Upgrade camera to interface
class CameraPipeline:
    def __init__(self, camera):
        self.camera = camera
        self.camera.start()
 
    def capture(self, exposure_time, gain, binning=1):
        exposure_time = np.clip(exposure_time, 1e-6, 30.0)
        gain = np.clip(gain, 1.0, 16.0)
        binning = int(np.clip(binning, 1, 4))
 
        frame = self.camera.capture(exposure_time, gain, binning)
        return frame
        processed_frame = self._process_frame(frame)
 
        return processed_frame
 
    def _process_frame(self, frame):
        resized = cv2.resize(frame, (224, 224)) # Resize to MobileNetV3 input

        return resized
 
    def shutdown(self):
        self.camera.stop()
 