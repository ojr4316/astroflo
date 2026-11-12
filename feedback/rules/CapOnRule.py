from feedback.metrics.QualityMetric import Metric
from feedback.rules.ClassificationRule import ClassificationRule

class CapOnRule(ClassificationRule):
    id = "cap_on"
    message = "Lens cap on?"
    severity = "error"

    def __init__(self, min_bg: float = 0.01, priority: int = 110):
        super().__init__(priority)
        self.min_bg = min_bg

    def evaluate(self, metrics: dict) -> bool:
        return metrics.get(Metric.MEAN, 0) < self.min_bg
