from capture.camera import Camera
import numpy as np
from PIL import Image
import time
from observation_context import CameraState

class FakeCamera(Camera):

    def __init__(self, camera_state: CameraState, fake_feed=[]):
        super().__init__(camera_state)
        self.fake_idx = 0
        self.fake_feed = fake_feed

    def start(self):
        super().start()
        print("Fake camera started!")

    def stop(self):
        super().stop()
        print("Fake camera stopped!")

    def _generate_fake_image(self, width=256, height=256):
        img = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        return Image.fromarray(img)

    def configure(self, exposure: int = 1_000_000, gain: float = 1.0):
        super().configure(exposure, gain)

    def capture(self):
        super().capture()
        time.sleep(self.camera_state.exposure / 1e6)

        if len(self.fake_feed) > 0:
            if self.fake_idx >= len(self.fake_feed):
                self.fake_idx = 0
            fake_image = self.fake_feed[self.fake_idx]
            self.fake_idx += 1
        else:
            fake_image = self._generate_fake_image()        
    
        self.queue.put(fake_image)
        return fake_image

