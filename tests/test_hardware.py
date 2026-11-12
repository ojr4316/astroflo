""" Real-hardware checks. Skipped unless run on the Pi with the hardware attached:

    ASTROFLO_HW_TESTS=1 pytest -m "pi_only or requires_camera or requires_tft"
"""
import time

import numpy as np
import pytest

from observation_context import ObservationContext


@pytest.mark.pi_only
@pytest.mark.requires_camera("finder")
def test_finder_camera_captures_frame():
    from capture.rpi_camera import RPiCamera
    ctx = ObservationContext()
    ctx.camera_state.exposure = 100_000
    cam = RPiCamera(ctx.camera_state)
    cam.start()
    try:
        frame = np.asarray(cam.capture())
    finally:
        cam.stop()
    assert frame.ndim == 3 and frame.shape[2] == 3


@pytest.mark.linux_only
@pytest.mark.requires_camera("imaging")
def test_sv105_connects_and_captures():
    from capture.sv105_camera import SV105Camera
    cam = SV105Camera()
    assert cam.connect(), "SV105 detected but could not be opened"
    try:
        cam.configure(10_000, 0)
        frame = cam.capture()
    finally:
        cam.close()
    assert frame is not None and frame.size > 0


@pytest.mark.requires_v4l2
@pytest.mark.requires_camera("imaging")
def test_sv105_reports_controls():
    from capture import v4l2_util
    device = v4l2_util.find_device()
    ctrls = v4l2_util.list_ctrls(device)
    assert all(v4l2_util.exposure_ctrl_names(ctrls))


@pytest.mark.pi_only
@pytest.mark.requires_tft
def test_tft_display_draws_and_reads_buttons():
    from PIL import Image
    from hardware.input import Input
    from hardware.tft_display import TFTDisplay
    display = TFTDisplay()
    display.draw_screen(Image.new("RGB", (240, 240), (40, 0, 0)))
    display.read_buttons(Input())
    time.sleep(0.2)
    display.clear()
