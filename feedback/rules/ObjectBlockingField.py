from feedback.metrics.QualityMetric import Metric
from feedback.rules.ClassificationRule import ClassificationRule

class ObjectBlockingField(ClassificationRule):
    id = "field_blocked"
    message = "Field blocked?"
    severity = "warning"

    def __init__(self, min_snr: float = 1.0, priority: int = 5):
        super().__init__(priority)
        self.min_snr = min_snr

    def evaluate(self, metrics: dict) -> bool:
        return metrics.get(Metric.SNR, 0) < self.min_snr
