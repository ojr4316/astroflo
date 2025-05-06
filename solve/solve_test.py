import os
from SolvePipeline import SolvePipeline
from solvers.astrometry_handler import AstrometryNetSolver


def main():
    image_dir = os.path.dirname(os.path.abspath(__file__))
    file = os.path.normpath(os.path.join(image_dir, "..", "test_data", "test.jpg"))
    solver = SolvePipeline(AstrometryNetSolver())
    a = solver.process(file)
    print(a)

if __name__ == "__main__":
    main()