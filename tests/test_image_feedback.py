""" Image feedback classification and analyzer feedback state """
import numpy as np
import pytest

import analyzer as analyzer_mod
from analyzer import Analyzer
from feedback.image_feedback import ImagingFeedback, FeedbackResult, OK

H, W = 600, 800
Y, X = np.mgrid[0:H, 0:W]


def blob(cx, cy, sigma, amp):
    return amp * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * sigma ** 2))


def star_field():
    rng = np.random.default_rng(0)
    img = np.full((H, W), 50.0) + rng.normal(0, 3, (H, W))
    for sx, sy in rng.integers(20, 580, (40, 2)):
        img += blob(sx, sy, 1.5, 200)
    return np.clip(img, 0, 255)


def defocused():  # broad, smooth glow with one hot pixel; bright enough to not be "blocked"
    img = blob(400, 300, 400, 100) + 20
    img[10, 10] = 255
    return img


def defocused_and_blocked():  # smooth and mostly dark: matches both blur and field-blocked
    img = blob(0, 0, 250, 80)
    img[300, 400] = 255
    return img


@pytest.fixture(scope="module")
def fb():
    return ImagingFeedback()


@pytest.mark.parametrize("image, expected", [
    (np.zeros((H, W)), "cap_on"),
    (np.full((H, W), 255.0), "over_exposed"),
    (defocused(), "blurred"),
    (defocused_and_blocked(), "blurred"),  # higher priority wins
    (star_field(), "ok"),
])
def test_classification(fb, image, expected):
    result = fb.classify(image.astype(np.float32))
    assert result.id == expected


def test_cap_on_message_and_severity(fb):
    r = fb.classify(np.zeros((H, W), np.float32))
    assert (r.message, r.severity) == ("Lens cap on?", "error")


def test_ok_result_has_named_metrics(fb):
    r = fb.classify(star_field().astype(np.float32))
    assert r.ok and r.severity is None
    assert set(r.metrics) == {"Mean", "StdDev", "Saturated", "Sharpness", "SNR"}
    assert all(isinstance(v, float) for v in r.metrics.values())


def test_rules_have_unique_ids_and_priorities(fb):
    assert len({r.id for r in fb.rules}) == len(fb.rules)
    assert len({r.priority for r in fb.rules}) == len(fb.rules)


WARN = FeedbackResult("blurred", "Out of focus", "warning", {"Sharpness": 0.001})


def test_feedback_before_first_frame():
    a = Analyzer()
    assert a.get_feedback() is OK
    assert a.get_feedback_with_age() == (OK, None)


def test_ok_frame_clears_warning():
    a = Analyzer()
    a.set_feedback(WARN)
    assert a.get_feedback() is WARN
    a.set_feedback(FeedbackResult("ok", "OK", None, {"Sharpness": 0.1}))
    assert a.get_feedback().ok


def test_warning_expires(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(analyzer_mod.time, "time", lambda: now[0])
    a = Analyzer()
    a.set_feedback(WARN)
    now[0] += 4.9
    assert a.get_feedback() is WARN
    now[0] += 0.2
    assert a.get_feedback().ok
