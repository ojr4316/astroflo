from feedback.metrics.QualityMetric import Metric
from feedback.rules.ClassificationRule import ClassificationRule

class BlurRule(ClassificationRule):
    def __init__(self, sharpness_threshold = 0.005, priority: int = 10):
        super().__init__(priority)
        self.sharpness_threshold = sharpness_threshold

    def evaluate(self, metrics: dict) -> bool:
        return metrics.get(Metric.SHARPNESS, float('inf')) < self.sharpness_threshold