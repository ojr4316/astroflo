import os
import numpy as np
from queue import Queue
from abc import ABC, abstractmethod
from observation_context import SolverState, TelescopeState
from analyzer import analyzer

class Solver(ABC):

    def __init__(self, solver_state: SolverState, telescope_state: TelescopeState):
        self.solver_state = solver_state
        self.telescope_state = telescope_state

    @abstractmethod
    def solve(self, image):
        """ Solve input image and return coordinates, or None if failed """
        return None

    def solver(self, capturer_queue: Queue): # Run in a separate thread to continuously solve images
        print( self.__class__.__name__ + " started solving")
        while True:
            latest = capturer_queue.get(block=True)
            if latest is None:
                continue
            result = self.solve(latest)
            if result is not None:
                coord, roll = result
                self.telescope_state.solve_result(coord, roll)
                analyzer.queue.put(latest)