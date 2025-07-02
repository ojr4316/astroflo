from solve.solver import Solver
import time

vega = (279.24372, 38.7861)
altair = (297.70505, 8.8712)

class FakeSolver(Solver):
    
    def solve(self, image):
        time.sleep(2)
        return ((image, altair, 100))