""" Plate solving with the pure-Python tetra3 package (any OS). Optional: pip install -r requirements-solver.txt """
import math

import numpy as np
from PIL import Image

if not hasattr(np, "math"):
    np.math = math  # tetra3 still uses np.math, removed in NumPy 2

from observation_context import SolverState, TelescopeState
from solve.solver import Solver


class Tetra3Solver(Solver):
    def __init__(self, solver_state: SolverState, telescope_state: TelescopeState, database: str = None):
        super().__init__(solver_state, telescope_state)
        from tetra3 import Tetra3
        self.t3 = Tetra3(database) if database else Tetra3()

    def solve(self, image):
        try:
            img = image if isinstance(image, Image.Image) else Image.fromarray(np.asarray(image))
            result = self.t3.solve_from_image(img.convert("L"), fov_estimate=self.solver_state.fov, fov_max_error=self.solver_state.fov * 0.5)
        except Exception as e:
            print(f"tetra3 solve failed: {e}")
            return None
        if result.get("RA") is None:
            return None
        return ((float(result["RA"]), float(result["Dec"])), float(result.get("Roll") or 0.0))
