"""
Automatic exposure/gain for the imaging camera.

Designed for a wide range of targets, from the Moon (very bright, fills the field at long focal
lengths) to faint star clusters in light-polluted skies (background-limited, needs the longest
exposure and highest gain available).

Policy:
- Measure median brightness (background / surface level) and saturated pixel fraction.
- Too dark  -> lengthen exposure first; raise gain only once exposure is at its maximum.
- Too bright -> lower gain first; shorten exposure only once gain is at its minimum.
- In band   -> unchanged (the band gives hysteresis so settings don't oscillate).
- Steps are multiplicative and larger when far from target, so going Moon -> cluster
  (~4 decades of exposure) converges in a handful of frames.
"""
from typing import Tuple

import numpy as np

from capture.imaging_camera import ImagingLimits

TARGET_LOW = 40          # median brightness band (0-255)
TARGET_HIGH = 110
TARGET_MID = 70
SATURATION_LEVEL = 250
MAX_SATURATED_FRACTION = 0.005   # >0.5% clipped pixels counts as overexposed (stars alone stay below)
HEAVY_SATURATION = 0.2           # median unreliable; take the biggest step down

MAX_STEP_UP = 4.0
MIN_STEP_UP = 1.25
MAX_STEP_DOWN = 0.25
MIN_STEP_DOWN = 0.8

GAIN_STEP_SMALL = 0.10   # fraction of the gain range
GAIN_STEP_LARGE = 0.25


def frame_stats(frame: np.ndarray) -> Tuple[float, float]:
    """ (median brightness, saturated fraction) on a downsampled grayscale view. """
    view = frame[::4, ::4]
    if view.ndim == 3:
        view = view.mean(axis=2)
    if view.dtype != np.uint8:  # normalise >8-bit frames to 0-255
        view = view.astype(np.float32) * (255.0 / max(1.0, float(np.iinfo(frame.dtype).max)))
    return float(np.median(view)), float((view >= SATURATION_LEVEL).mean())


def classify(median: float, saturated: float) -> int:
    """ -1 too dark, 0 ok, +1 too bright """
    if saturated > MAX_SATURATED_FRACTION or median > TARGET_HIGH:
        return 1
    if median < TARGET_LOW:
        return -1
    return 0


def _gain_step(limits: ImagingLimits, large: bool) -> float:
    return (limits.max_gain - limits.min_gain) * (GAIN_STEP_LARGE if large else GAIN_STEP_SMALL)


def next_settings(frame: np.ndarray, exposure_us: float, gain: float, limits: ImagingLimits) -> Tuple[float, float]:
    median, saturated = frame_stats(frame)
    state = classify(median, saturated)
    exposure_us = limits.clamp_exposure(exposure_us)
    gain = limits.clamp_gain(gain)

    if state == 0:
        return exposure_us, gain

    if state > 0:
        if saturated > HEAVY_SATURATION:
            ratio = MAX_STEP_DOWN
        else:
            ratio = min(MIN_STEP_DOWN, max(MAX_STEP_DOWN, TARGET_MID / max(median, 1.0)))
        if gain > limits.min_gain:
            gain = limits.clamp_gain(gain - _gain_step(limits, large=ratio <= 0.5))
        else:
            exposure_us = limits.clamp_exposure(exposure_us * ratio)
        return exposure_us, gain

    ratio = max(MIN_STEP_UP, min(MAX_STEP_UP, TARGET_MID / max(median, 1.0)))
    if exposure_us < limits.max_exposure_us:
        exposure_us = limits.clamp_exposure(exposure_us * ratio)
    else:
        gain = limits.clamp_gain(gain + _gain_step(limits, large=ratio >= 2.0))
    return exposure_us, gain
