import time
from typing import List, Optional
from threading import Thread, Lock
from PIL import Image
from capture.camera import Camera
from solve.solver import Solver
from astronomy.telescope import Telescope
from astronomy.stellarium import StellariumConnection
from astronomy.analyze import ImageAnalysis
from operation import OperationManager
from capture.adjuster import Adjuster
from utils import solve_rotation

class Astroflo:

    capturer: Camera = None
    solver: Solver = None
    
    def __init__(self, capturer: Camera, solver: Solver, scope: Telescope):
        self.capturer = capturer
        self.solver = solver
        self.scope = scope
        
        self.latest = None
        self.latest_timestamp = None
        self.state_lock = Lock()
    
        self.fails = 0
        self.running = False

        self.configuring = False
        self.latest_image = None # Stored for rendering

        self.analysis = ImageAnalysis() 
        self.adjuster = Adjuster(self.capturer)
        self.stellarium = StellariumConnection()
        self._pipeline = Thread(target=self.pipeline, daemon=True)

    def start(self):
        self.capturer.start()
        
        # Configure Solver
        self.solver.fov = 22

        self.running = True
        self._pipeline.start()

        if OperationManager.stellarium_server:
            self.stellarium.run_server()

    def stop(self):
        self.running = False
        if self._pipeline.is_alive():
            self._pipeline.join(timeout=2.0)
    
    def configure_camera(self, img):
        if self.configuring and hasattr(self, "analysis"):
            loc = self.analysis.find_brightest(img)
            if loc is not None:
                y, x, _ = loc[0]
                half_size = 40
                box = (
                    max(x - half_size, 0),
                    max(y - half_size, 0),
                    min(x + half_size, img.shape[1]),
                    min(y + half_size, img.shape[0])
                )
                cropped = Image.fromarray(img).crop(box)
                self.latest_image = cropped.resize((240, 240), resample=Image.BILINEAR)
                return True
        return False

    def pipeline(self):
        self.running = True
        while self.running:
            img = self.capturer.capture()
            if img is not None:
                timestamp = time.time()
                if OperationManager.perform_analysis:
                    self.analysis.add_image(img)
                
                configuring = self.configure_camera(img)
                if configuring:
                    continue

                result = self.solver.solve(img)
                with self.state_lock:
                    if result is not None:
                        self.fails = 0
                        if (not self.latest_timestamp or timestamp > self.latest_timestamp) and result[1] != 'Failed':
                            self.set_latest(result, timestamp)
                    elif OperationManager.dynamic_adjust:
                        self.adjuster.fail()
            time.sleep(0.1)

    def set_latest(self, result, timestamp):
        coords, roll = result
        ra, dec = coords
        self.latest_timestamp = timestamp

        self.scope.solve_result(ra, dec, roll) # move
        if self.latest is not None:
            old_coords, old_roll = self.latest['result']
            ora, odec = round(old_coords[0], 2), round(old_coords[1], 2)
            rra, rdec = round(ra, 2), round(dec, 2)
            new_result = ora != rra or odec != rdec
            if not new_result:
                self.latest = {
                    'result': result,
                    'timestamp': timestamp
                }
                return

        self.latest = {
            'result': result,
            'timestamp': timestamp
        }
        
        # Only update scope (renders) and stellarium if new result
        
        print(f"found new position: {ra}, {dec} at {timestamp}")
        if OperationManager.stellarium_server:
            ra, dec = self.scope.get_position()
            self.stellarium.update_position(ra, dec)
        if OperationManager.dynamic_adjust:
            self.adjuster.success()
        
    def stop_configuring(self):
        self.configuring = False
        self.latest_image = None


