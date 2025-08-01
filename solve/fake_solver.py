from solve.solver import Solver
import time
from observation_context import SolverState, TelescopeState

polaris = (37.80326, 89.2592)
polaris_wrong2 = (19.05591, 87.1399) # nearby bright star, testing cam offset
polaris_near = (23.44546, 89.0100) # nearby bright star, testing cam offset
polaris_wrong = (22.81894, 88.6517) # nearby bright star, testing cam offset

vega = (279.24372, 38.7861)
altair = (297.70505, 8.8712)
altair_off = (294.70505, 7.7712)
mizar = (200.98349, 54.9302)
alkaid = (206.88404, 49.3178)

pleiades = (56.74689, 24.1160)

s = (2.33984, -1.4648)
c = (17.15721, -5.3056)

class FakeSolver(Solver):
    
    target = pleiades
    
    def __init__(self, solver_state: SolverState, telescope_state: TelescopeState):
        super().__init__(solver_state, telescope_state)

    def solve(self, image):
        time.sleep(0.3)
        #self.target = (self.target[0] - 0.1, self.target[1] + 0.3)
        return (self.target, 0)