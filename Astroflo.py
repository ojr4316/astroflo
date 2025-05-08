from typing import List, Optional
from queue import Queue
from threading import Thread, Lock
import time
import os
from datetime import datetime
from capture.CameraPipeline import CameraPipeline
from solve.SolvePipeline import SolvePipeline
from capture.camera_controllers.Camera import Camera
from solve.solvers.Solver import Solver
from clean.ImageProcessor import ImageProcessor

class Astroflo:
    capturer: Camera = None
    solver: Solver = None
    processors: List[ImageProcessor] = []
    
    def __init__(self, capturer: Camera, solver: Solver, processors: Optional[List[ImageProcessor]] = None):
        self.capturer = capturer
        self.solver = solver
        self.capture_pipeline = CameraPipeline(capturer)
        self.solve_pipeline = SolvePipeline(solver)
        self.processors = processors or []
        
        self.latest = None
        self.latest_timestamp = None
        self.state_lock = Lock()
        
        self.capture_thread = Thread(target=self._capture_loop, daemon=True)
        self.running = False
        
        self.start()
    
    def start(self):
        self.running = True
        self.capture_thread.start()
        print("Astroflo started!~")
   
    def stop(self):
        self.running = False
        if self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        print("Astroflo stopped!~")
    
    def _capture_loop(self):
        while self.running:
            img = self.capture_pipeline.capture()
            if img is not None:
                timestamp = datetime.now()
                Thread(target=self._process_image, args=(img, timestamp), daemon=True).start()
    
    def _process_image(self, img, timestamp):
        try:
            processed_img = img
            for processor in self.processors:
                processed_img = processor.process(processed_img)
            
            result = self.solve_pipeline.solve(processed_img)
            
            with self.state_lock:
                if not self.latest_timestamp or timestamp > self.latest_timestamp:
                    self.latest = {
                        'result': result,
                        'timestamp': timestamp
                    }
                    self.latest_timestamp = timestamp
                    
                    # Discard image
                    image, coord, odds = result
                    os.remove(f"./{image}")
                    print("New result found!")


                else:
                    print(f"Discarded older result from {timestamp}")
        except Exception as e:
            print(f"Error processing image from {timestamp}: {e}")
    
    def get_latest_result(self):
        with self.state_lock:
            return self.latest
