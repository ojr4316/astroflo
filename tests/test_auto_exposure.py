import numpy as np

from capture.auto_exposure import next_settings, frame_stats
from capture.imaging_camera import ImagingLimits
from capture.fake_imaging_camera import FakeImagingCamera

LIMITS = ImagingLimits(min_exposure_us=100, max_exposure_us=1_000_000, min_gain=0, max_gain=100)


def flat(value, saturated_fraction=0.0, shape=(200, 200)):
    img = np.full(shape, value, dtype=np.uint8)
    n = int(saturated_fraction * img.size)
    img.flat[:n] = 255
    return img


def test_frame_stats():
    median, sat = frame_stats(flat(80))
    assert median == 80 and sat == 0


def test_in_band_unchanged():
    assert next_settings(flat(70), 10_000, 20, LIMITS) == (10_000, 20)


def test_dark_increases_exposure_not_gain():
    exp, gain = next_settings(flat(20), 10_000, 20, LIMITS)
    assert exp > 10_000 and gain == 20


def test_dark_at_max_exposure_increases_gain():
    exp, gain = next_settings(flat(20), 1_000_000, 20, LIMITS)
    assert exp == 1_000_000 and gain > 20


def test_gain_clamped_at_max():
    exp, gain = next_settings(flat(5), 1_000_000, 100, LIMITS)
    assert (exp, gain) == (1_000_000, 100)


def test_bright_reduces_gain_first():
    exp, gain = next_settings(flat(200), 10_000, 50, LIMITS)
    assert exp == 10_000 and gain < 50


def test_bright_at_min_gain_reduces_exposure():
    exp, gain = next_settings(flat(200), 10_000, 0, LIMITS)
    assert exp < 10_000 and gain == 0


def test_saturation_counts_as_overexposed():
    exp, gain = next_settings(flat(60, saturated_fraction=0.05), 10_000, 0, LIMITS)
    assert exp < 10_000


def test_exposure_clamped_at_min():
    exp, gain = next_settings(flat(255), 100, 0, LIMITS)
    assert (exp, gain) == (100, 0)


def _converge(cam, exposure, gain, steps=40):
    for _ in range(steps):
        cam.configure(exposure, gain)
        exposure, gain = next_settings(cam.capture(), cam.exposure_us, cam.gain, cam.limits)
    cam.configure(exposure, gain)
    return frame_stats(cam.capture())[0], exposure, gain


def test_converges_on_moon_from_dim_settings():
    moon = FakeImagingCamera(scene_brightness=1_000_000)  # saturates at all but the shortest exposures
    moon.connect()
    median, exposure, gain = _converge(moon, 1_000_000, 100)
    assert 40 <= median <= 110
    assert gain == moon.limits.min_gain


def test_converges_on_dim_cluster_using_gain():
    cluster = FakeImagingCamera(scene_brightness=5)  # needs max exposure and gain
    cluster.connect()
    median, exposure, gain = _converge(cluster, 1_000, 0)
    assert 40 <= median <= 110
    assert exposure == cluster.limits.max_exposure_us and gain > 0
