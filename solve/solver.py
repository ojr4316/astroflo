from abc import ABC, abstractmethod

class Solver(ABC):
    
    def __init__(self):
        self.target_pixel = None # where in the image you are asking for coordinates

    @abstractmethod
    def solve(self, image):
        """ Solve input image and return coordinates, or None if failed """
        return None