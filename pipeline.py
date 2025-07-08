from typing import List, Optional
from threading import Thread, Lock
from datetime import timedelta
import time
import os
from datetime import datetime
from capture.camera import Camera
from solve.solver import Solver
from clean.image_processor import ImageProcessor
from astronomy.telescope import Telescope
from astronomy.stellarium import StellariumConnection
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u
from astronomy.analyze import ImageAnalysis
from operation import OperationManager

class Astroflo:
    capturer: Camera = None
    solver: Solver = None
    processors: List[ImageProcessor] = []
    ## Fail Manager
    ## 
    def __init__(self, capturer: Camera, solver: Solver, scope: Telescope, processors: Optional[List[ImageProcessor]] = None):
        self.capturer = capturer
        self.solver = solver
        self.scope = scope
        self.processors = processors or []
        
        self.latest = None
        self.latest_timestamp = None
        self.state_lock = Lock()
    
        self.fails = 0
        self.running = False

        self._pipeline = Thread(target=self.pipeline, daemon=True)
        if OperationManager.perform_analysis:
            self.analysis = ImageAnalysis()        
    
    def start(self):
        # Configure camera resasonably before start
        self.capturer.configure(1_000_000)
        self.capturer.start()
        
        # Configure Solver
        self.solver.limit = 30
        self.solver.scale = 19
        self.solver.downsample = 4
        self.running = True
        self._pipeline.start()

        if OperationManager.stellarium_server:
            self.stellarium = StellariumConnection(self.scope)
            self.stellarium.run_server()

    def stop(self):
        self.running = False
        if self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
    
    def pipeline(self):
        self.running = True
        while self.running:
            img = self.capturer.capture()
            if img is not None:
                timestamp = datetime.now()
                if OperationManager.perform_analysis:
                    self.analysis.add_image(img)
                result = self.solver.solve(img)
                with self.state_lock:
                    if result is not None:
                        self.fails = 0
                        if (not self.latest_timestamp or timestamp > self.latest_timestamp) and result[1] != 'Failed':
                            self.set_latest(result, timestamp)
                    else:
                        pass # TODO: add fail manager? 

    def set_latest(self, result, timestamp):
        image, coords, odds = result
        self.latest = {
            'result': result,
            'timestamp': timestamp
        }
        self.latest_timestamp = timestamp
        ra, dec = coords
        self.scope.set_position(ra, dec)
        print(f"found new position: {ra}, {dec} at {timestamp}")
        self.stellarium.new_position()

    def offset_pos_to_brightest_nearby(self):
        scope = self.scope
        ra, dec = scope.position # raw position, old offset cant bias
        stars = scope.target_manager.stars
        r = stars.radius_from_telescope(self.scope.focal_length, self.scope.eyepiece, self.scope.eyepiece_fov) * 4
        nearby = self.stars.search_by_coordinate(ra=ra, dec=dec, radius=r)
        
        if len(nearby) == 0:
            print("FAIL")
            return
        else:
            brightest = nearby[0]
            for s in nearby:
                if s['Vmag'] < brightest: # TODO: fix for negative amgs
                    brightest = s
            tra, tdec = brightest['RAdeg'], brightest['DEdeg']

            scope.set_camera_offset(ra-tra, dec-tdec)
            print(self.scope.camera_offset)



