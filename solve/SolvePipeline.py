
class SolvePipeline:

    def __init__(self, solver):
        self.solver = solver 

        self.solve_queue = []

    def process(self, image_path):
        if len(self.solve_queue) > 0:
            self.solve_queue.append(image_path)
        else:
            return self.solver.solve(image_path)