import os
import time
import numpy as np
from queue import Empty, Queue
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

    solves = 0  # successful solves (for status/tests)

    def process(self, image):
        """ Solve one frame and publish the result; returns the result or None """
        self.solver_state.last_solved = time.time()
        analyzer.queue.put(image)
        result = self.solve(image)
        if result is not None:
            coord, roll = result
            self.telescope_state.solve_result(coord, roll)
            self.solves += 1
        return result

    def solver(self, capturer_queue: Queue, stop_event=None): # Run in a separate thread to continuously solve images
        print( self.__class__.__name__ + " started solving")
        while stop_event is None or not stop_event.is_set():
            try:
                latest = capturer_queue.get(timeout=0.5)
            except Empty:
                continue
            if latest is None:
                continue
            self.process(latest)