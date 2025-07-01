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

        self.capture_thread = Thread(target=self._capture_loop, daemon=True)
        if OperationManager.perform_analysis:
            self.analysis = ImageAnalysis()        
    
    def start(self):
        # Configure camera resasonably before start
        self.capturer.configure(15_000_000)
        self.capturer.start()
        
        # Configure Solver
        self.solver.limit = 30
        self.solver.scale = 19
        self.solver.downsample = 4
        self.running = True
        self.capture_thread.start()

        if OperationManager.stellarium_server:
            self.stellarium = StellariumConnection(self.scope)
            self.stellarium.run_server()

    def stop(self):
        self.running = False
        if self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
    
    def synchronous_loop(self):
        self.running = True
        while self.running:
            img = self.capturer.capture()
            if img is not None:
                timestamp = datetime.now()
                if OperationManager.perform_analysis:
                    self.analysis.run()
                result = self.solver.solve(img)
                with self.state_lock:
                    if result is not None:
                        self.fails = 0
                        if (not self.latest_timestamp or timestamp > self.latest_timestamp) and result[1] != 'Failed':
                            self.set_latest(result, timestamp)
                    else:
                        pass # TODO: add fail manager? 

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
            with self.state_lock:
                if result is not None:
                    self.fails = 0
                    if (not self.latest_timestamp or timestamp > self.latest_timestamp) and result[1] != 'Failed':
                        self.set_latest(result, timestamp)
                else: # Adjust exposure until solvable
                    self.fails += 1
                    if self.fails >= 10:
                        return
                        self.fails = -5
                        print("Adjusting exposure")
                        current = self.capturer.exposure
                        self.capturer.configure(current+100_000)
        except Exception as e:
            print(f"Error processing image from {timestamp}: {e}")

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
            
     
    def drift(self, interval=60*30):
        with self.state_lock:
            if self.latest is None:
                return
            utc = self.scope.time.utc_datetime()
            ra, dec = self.scope.position # no cam offset

            start = Time(utc)
            end = start + interval * u.s

            icrs = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs')
            altaz = icrs.transform_to(AltAz(obstime=start, location=self.scope.location))
            drifted = altaz.transform_to(AltAz(obstime=end, location=self.scope.location)).transform_to('icrs')

            new_utc = utc + timedelta(seconds=interval)
            self.scope.set_time(new_utc)
            self.scope.set_position(drifted.ra.deg, drifted.dec.deg)
            self.stellarium.new_position()
            return drifted.ra.deg, drifted.dec.deg

