from feedback_classifier.metrics.QualityMetric import Metric
from feedback_classifier.rules.ClassificationRule import ClassificationRule

class BlurRule(ClassificationRule):
    def __init__(self, sharpness_threshold = 1e-3, priority: int = 10):
        super().__init__(priority)
        self.sharpness_threshold = sharpness_threshold

    def evaluate(self, metrics: dict) -> bool:
        return metrics.get(Metric.SHARPNESS, float('inf')) < self.sharpness_threshold