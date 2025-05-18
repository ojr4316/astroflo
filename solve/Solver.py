from abc import ABC, abstractmethod

class Solver(ABC):
    
    @abstractmethod
    def solve(self, image):
        """ Solve input image and return coordinates, or None if failed """
        pass