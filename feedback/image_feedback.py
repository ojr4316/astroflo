""" Rule-based feedback for astronomical imaging """
import numpy as np
import cv2
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from feedback.metrics.QualityMetric import QualityMetric, Mean, StdDev, Saturated, Sharpness, SignalToNoiseRatio
from feedback.metrics.StarCount import StarCount
from feedback.rules.ClassificationRule import ClassificationRule
from feedback.rules.CapOnRule import CapOnRule
from feedback.rules.OverExposedRule import OverExposedRule
from feedback.rules.BlurRule import BlurRule
from feedback.rules.ObjectBlockingField import ObjectBlockingField

@dataclass(frozen=True)
class FeedbackResult:
    """ Outcome of classifying one frame. severity is None when no rule matched. """
    id: str
    message: str
    severity: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.id == OK.id


OK = FeedbackResult("ok", "OK")


class ImagingFeedback:
    def __init__(self):
        self.metrics: Dict[str, QualityMetric] = {}
        self.rules: List[ClassificationRule] = []
        
        # Initialize with default metrics to calcuate and rules to justify feedback
        self.add_default_metrics()
        self.add_default_rules()

    def add_metric(self, metric: QualityMetric) -> None:
        self.metrics[metric.name] = metric
    
    def add_rule(self, rule: ClassificationRule) -> None:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True) # sort by highest priority
    
    def add_default_metrics(self) -> None:
        self.add_metric(Mean())
        self.add_metric(StdDev())
        self.add_metric(Saturated())
        self.add_metric(Sharpness())
        self.add_metric(SignalToNoiseRatio())
    
    def add_default_rules(self) -> None:
        self.add_rule(CapOnRule())
        self.add_rule(OverExposedRule())
        self.add_rule(BlurRule())
        self.add_rule(ObjectBlockingField())
    
    def compute_metrics(self, image: np.ndarray) -> Dict[str, float]:
        metrics = {}
        for name, metric in self.metrics.items():
            metrics[name] = metric.compute(image)
        return metrics
    
    def classify(self, image: np.ndarray) -> FeedbackResult:
        # Normalize
        if image.max() > 1.0:
            normalized_image = image / image.max()
        else:
            normalized_image = image

        # Resize
        if normalized_image.shape[0] > 1000 or normalized_image.shape[1] > 1000:
            normalized_image = cv2.resize(normalized_image, (1000, 1000), interpolation=cv2.INTER_AREA)
        
        metrics = self.compute_metrics(normalized_image)
        named = {getattr(k, "value", k): float(v) for k, v in metrics.items()}

        # Evaluate all rules in priority order; first match wins
        for rule in self.rules:
            if rule.evaluate(metrics):
                return FeedbackResult(rule.id, rule.message, rule.severity, named)

        return FeedbackResult(OK.id, OK.message, None, named)
    
feedback = ImagingFeedback()
