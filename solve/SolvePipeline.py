
class SolvePipeline:

    def __init__(self, solver):
        self.solver = solver

    def solve(self, image_path):
        return self.solver.solve(image_path)