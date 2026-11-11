import os
import time

import pytest

from observation_context import ObservationContext
from capture.fake_imaging_camera import FakeImagingCamera
from capture.image_store import ImageStore
from capture.imaging import ImagingController, imaging_field_radius, target_in_field


@pytest.fixture
def ctx():
    c = ObservationContext()
    c.target_state.set_target(83.82, -5.39, "M42")
    c.telescope_state.position = (83.82, -5.39)
    c.solver_state.last_solved = time.time()
    return c


def make(ctx, tmp_path, scene_brightness=5_000, **kw):
    cam = FakeImagingCamera(scene_brightness=scene_brightness)
    controller = ImagingController(cam, ctx, ImageStore(str(tmp_path)), reconnect_interval=0, idle_sleep=0, **kw)
    return cam, controller


def files(tmp_path, sub):
    d = os.path.join(str(tmp_path), sub)
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def test_field_radius_for_1200mm():
    radius = imaging_field_radius(ObservationContext().telescope_optics)
    assert 0.14 < radius < 0.17


def test_target_in_field_conditions(ctx):
    assert target_in_field(ctx)
    ctx.telescope_state.position = (83.82 + 1.0, -5.39)
    assert not target_in_field(ctx)  # out of field
    ctx.telescope_state.position = (83.82, -5.39)
    ctx.solver_state.last_solved = time.time() - 11
    assert not target_in_field(ctx)  # stale solve
    ctx.solver_state.last_solved = time.time()
    ctx.target_state.ra = None
    assert not target_in_field(ctx)  # no target


def test_auto_disabled_by_default_saves_nothing(ctx, tmp_path):
    _, controller = make(ctx, tmp_path)
    for _ in range(5):
        controller.step()
    assert ctx.imaging_state.connected
    assert files(tmp_path, "M42") == []


def test_auto_saves_only_while_in_field(ctx, tmp_path):
    _, controller = make(ctx, tmp_path)
    ctx.imaging_state.auto_enabled = True
    for _ in range(5):
        assert controller.step()
    assert len(files(tmp_path, "M42")) == 5

    ctx.telescope_state.position = (100.0, 20.0)
    for _ in range(3):
        assert not controller.step()
    assert len(files(tmp_path, "M42")) == 5
    assert ctx.imaging_state.frames_saved == 5


def test_auto_adjusts_exposure(ctx, tmp_path):
    cam, controller = make(ctx, tmp_path, scene_brightness=500)  # too dark at the start exposure
    ctx.imaging_state.auto_enabled = True
    start = cam.exposure_us
    for _ in range(5):
        controller.step()
    assert cam.exposure_us != start
    assert ctx.imaging_state.exposure_us == cam.exposure_us


def test_manual_capture_one_frame(ctx, tmp_path):
    ctx.target_state.ra = None  # manual works without a target
    _, controller = make(ctx, tmp_path)
    ctx.imaging_state.manual_requested.set()
    controller.step()
    controller.step()
    assert len(files(tmp_path, "manual")) == 1
    assert ctx.imaging_state.last_result == "Saved"


def test_manual_capture_during_auto_then_resumes(ctx, tmp_path):
    _, controller = make(ctx, tmp_path)
    ctx.imaging_state.auto_enabled = True
    controller.step()
    ctx.imaging_state.manual_requested.set()
    controller.step()
    controller.step()
    assert len(files(tmp_path, "manual")) == 1
    assert len(files(tmp_path, "M42")) == 2


def test_manual_capture_disconnected_fails(ctx, tmp_path):
    cam, controller = make(ctx, tmp_path)
    cam.present = False
    ctx.imaging_state.manual_requested.set()
    controller.step()
    assert files(tmp_path, "manual") == []
    assert ctx.imaging_state.last_result == "Failed"


def test_disconnect_and_reconnect(ctx, tmp_path):
    cam, controller = make(ctx, tmp_path)
    controller.step()
    assert ctx.imaging_state.connected
    cam.present = False
    controller.step()
    assert not ctx.imaging_state.connected
    cam.present = True
    controller.step()
    assert ctx.imaging_state.connected
