import os
from SolvePipeline import SolvePipeline
from solvers.astrometry_handler import AstrometryNetSolver


def main():
    dir = os.path.dirname(os.path.abspath(__file__))
    file = os.path.normpath(os.path.join(dir, "..", "test_data", "test.jpg"))
    solver = SolvePipeline(AstrometryNetSolver())
    a = solver.process(file)
    print(a)

if __name__ == "__main__":
    main()