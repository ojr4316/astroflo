from abc import ABC, abstractmethod
from typing import Dict

class ClassificationRule(ABC):

    def __init__(self, priority: int = 0):
        self.priority = priority

    @abstractmethod
    def evaluate(self, metrics: Dict[str, float]) -> bool:
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__

