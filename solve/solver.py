import os
import numpy as np
from abc import ABC, abstractmethod

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OFFSET_FILE = os.path.join(BASE_DIR, "..", "offset.npy")

class Solver(ABC):
    
    def __init__(self):
        self.target_pixel = None # where in the image you are asking for coordinates
        if os.path.exists(OFFSET_FILE):
            print("loading previously set offsets")
            offsets = np.load(OFFSET_FILE)
            print(offsets)
            self.target_pixel = offsets
    
    def save_offset(self, offset):
        self.target_pixel = offset
        np.save(OFFSET_FILE, offset)

    @abstractmethod
    def solve(self, image):
        """ Solve input image and return coordinates, or None if failed """
        return None