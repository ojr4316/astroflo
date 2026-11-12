from feedback.metrics.QualityMetric import Metric
from feedback.rules.ClassificationRule import ClassificationRule

class OverExposedRule(ClassificationRule):
    id = "over_exposed"
    message = "Over-exposed - lower exposure or gain"
    severity = "warning"

    def __init__(self, saturation_threshold: float = 0.01, priority: int = 100):
        super().__init__(priority)
        self.saturation_threshold = saturation_threshold

    def evaluate(self, metrics: dict) -> bool:
        return metrics.get(Metric.SATURATED, 1.0) > self.saturation_threshold
