import os
import sys
import pathlib
from PIL import Image
import cv2
import time
import math
import numpy as np
np.math = math
from solve.solver import Solver

# Make sure you're importing the package, not the module
if os.name == 'nt':
    sys.path.insert(0, str(pathlib.Path("C:/Users/314ow/cedar-solve").resolve()))
else:
    sys.path.insert(0, str(pathlib.Path("/home/owen/cedar-solve").resolve()))

from tetra3.tetra3 import Tetra3
from tetra3 import cedar_detect_client

# Actually Cedar
class Tetra3Solver(Solver):

    def __init__(self, fov=22):
        super().__init__()
        self.t3 = Tetra3()
        self.cedar_detect = cedar_detect_client.CedarDetectClient()
        #self.t3.generate_database(min_fov=15, max_fov=20, star_max_magnitude=7, save_as='default_database', star_catalog="bsc5")
        self.fov = fov # TODO: set with camera


    def solve(self, image):
        try:
            image = np.array(image)
            if image.ndim == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            #processed = tetra3.crop_and_downsample_image(image, downsample=0, return_offsets=True)
            #image, offsets = processed
            centroids = self.cedar_detect.extract_centroids(image, sigma=8, use_binned=True)
            target_pixel = None
            if self.target_pixel is not None:
                target_pixel = (self.target_pixel[0], self.target_pixel[1])
            result = self.t3.solve_from_centroids(centroids, fov_estimate=self.fov, size=(image.shape[1], image.shape[0]), target_pixel=target_pixel) # much faster than using Image
            #result = self.t3.solve_from_image(Image.fromarray(image), fov_estimate=self.fov, fov_max_error=1, pattern_checking_stars=20)
            print(result)
            if self.target_pixel is not None:
                ra = result['RA_target']
                dec = result['Dec_target']
            else:
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