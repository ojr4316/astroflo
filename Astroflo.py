from typing import List, Optional
from queue import Queue
from threading import Thread, Lock
import time
import os
from datetime import datetime
from capture.Camera import Camera
from solve.Solver import Solver
from clean.ImageProcessor import ImageProcessor
from astronomy.Telescope import Telescope
class Astroflo:
    capturer: Camera = None
    solver: Solver = None
    processors: List[ImageProcessor] = []
    
    def __init__(self, capturer: Camera, solver: Solver, scope: Telescope, processors: Optional[List[ImageProcessor]] = None):
        self.capturer = capturer
        self.solver = solver
        self.scope = scope
        self.processors = processors or []
        
        self.latest = None
        self.latest_timestamp = None
        self.state_lock = Lock()
        
        self.capture_thread = Thread(target=self._capture_loop, daemon=True)
        self.running = False
    
    def start(self):
        self.running = True
        self.capturer.start()

        self.capturer.configure(3_000_000) # TODO: configure camera reasonably
        self.solver.limit = 10 # TODO: configure sovler reasonably
        #self.solver.scale = 19
    
        self.capture_thread.start()
   
    def stop(self):
        self.running = False
        if self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
    
    def _capture_loop(self):
        while self.running:
            img = self.capturer.capture()
            if img is not None:
                timestamp = datetime.now()
                Thread(target=self._process_image, args=(img, timestamp), daemon=True).start()
    
    def _process_image(self, img, timestamp):
        try:
            processed_img = img
            for processor in self.processors:
                processed_img = processor.process(processed_img)
            
            result = self.solver.solve(processed_img)
            image, coords, odds = result
            with self.state_lock:
                if (not self.latest_timestamp or timestamp > self.latest_timestamp) and result[1] != 'Failed':
                    self.latest = {
                        'result': result,
                        'timestamp': timestamp
                    }
                    self.latest_timestamp = timestamp
                    ra, dec = coords
                    self.scope.set_position(ra, dec)
                os.remove(f"./{image}") # Discard image
        except Exception as e:
            print(f"Error processing image from {timestamp}: {e}")
    
    def get_latest_result(self):
        with self.state_lock:
            return self.latest

