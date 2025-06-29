from solve.solver import Solver

class FakeSolver(Solver):
    
    def solve(self, image):
        return ((image, (88.79, 7.40), 100))