from solve.solver import Solver
import time

polaris = (37.80326, 89.2592)
polaris_wrong2 = (19.05591, 87.1399) # nearby bright star, testing cam offset
polaris_near = (23.44546, 89.0100) # nearby bright star, testing cam offset
polaris_wrong = (22.81894, 88.6517) # nearby bright star, testing cam offset

vega = (279.24372, 38.7861)
altair = (297.70505, 8.8712)

class FakeSolver(Solver):
    
    def solve(self, image):
        time.sleep(2)
        return ((image, polaris_wrong, 100))