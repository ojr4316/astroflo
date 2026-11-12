""" Cedar (cedar-detect centroiding + cedar-solve tetra3). Pi/Linux only: imported lazily by backends.py.
The cedar-solve checkout path comes from ASTROFLO_CEDAR_PATH or settings.runtime.cedar_path. """
import os
import sys
import cv2
import math
import numpy as np
np.math = math
from solve.solver import Solver
from observation_context import SolverState, TelescopeState


def import_cedar(cedar_path: str = None):
    """ Put the cedar-solve checkout first on sys.path (so its tetra3 package wins) and import it """
    if cedar_path and os.path.isdir(cedar_path):
        path = os.path.abspath(cedar_path)
        if path not in sys.path:
            sys.path.insert(0, path)
    from tetra3.tetra3 import Tetra3
    from tetra3 import cedar_detect_client
    return Tetra3, cedar_detect_client


# Actually Cedar
class CedarSolver(Solver):

    def __init__(self, solver_state: SolverState, telescope_state: TelescopeState, cedar_path: str = None):
        super().__init__(solver_state, telescope_state)
        Tetra3, cedar_detect_client = import_cedar(cedar_path)
        self.t3 = Tetra3()
        self.cedar_detect = cedar_detect_client.CedarDetectClient()

    def solve(self, image):
        try:
            image = np.array(image)
            if image.ndim == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            centroids = self.cedar_detect.extract_centroids(image, sigma=8, use_binned=True)

            target_pixel = None # by default, just solve for center of image
            if self.solver_state.target_pixel is not None: # if target pixel is set, use it
                target_pixel = (self.solver_state.target_pixel[0], self.solver_state.target_pixel[1])
            result = self.t3.solve_from_centroids(centroids, fov_estimate=self.solver_state.fov, size=(image.shape[1], image.shape[0]), target_pixel=target_pixel) # much faster than using Image

            ra = dec = None
            if self.solver_state.target_pixel is not None and "RA_target" in result:
                ra = result['RA_target']
                dec = result['Dec_target']
            elif "RA" in result:
                ra = result['RA']
                dec = result['Dec']
            roll = result['Roll']
            
            if ra is not None:
                 coords = (ra, dec)
                 return (coords, roll)   
        except Exception as e:
            print(e)     

        return None
    
    def cleanup(self):
        if self.cedar_detect is not None:
            del self.cedar_detect
            self.cedar_detect = None
        self.t3 = None