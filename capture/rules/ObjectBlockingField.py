from metrics.QualityMetric import Metric
from rules.ClassificationRule import ClassificationRule

class ObjectBlockingField(ClassificationRule):
    def __init__(self, min_stars: int = 10, min_brightness: float = 1e-2, priority: int = 5):
        super().__init__(priority)
        self.min_stars = min_stars
        self.min_brightness = min_brightness

    def evaluate(self, metrics: dict) -> bool:
        return metrics.get(Metric.MEAN, 0) < self.min_brightness and metrics.get(Metric.STARCOUNT, float('inf') < self.min_stars)