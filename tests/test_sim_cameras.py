""" Simulated finder and imaging cameras (no hardware, any OS) """
import os
import time

import numpy as np
import pytest
from PIL import Image

import backends
from capture.fake_camera import FakeCamera, ImageFolderCamera
from capture.fake_imaging_camera import FakeImagingCamera
from config import Settings
from observation_context import CameraState, ObservationContext

TEST_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")


def write_images(folder, values):
    """ Solid-color images named in an order different from creation order """
    folder.mkdir(exist_ok=True)
    for i, v in enumerate(values):
        Image.new("L", (8, 6), v).save(folder / f"img_{i}.png")
    return folder


def started(cam):
    cam.running = True
    return cam


def test_replays_folder_in_name_order_and_loops(tmp_path):
    folder = write_images(tmp_path / "imgs", [10, 20, 30])
    cam = started(ImageFolderCamera(CameraState(), str(folder), simulate_exposure=False))
    means = [int(cam.capture().mean()) for _ in range(5)]
    assert means == [10, 20, 30, 10, 20]


def test_frames_are_rgb_uint8(tmp_path):
    folder = write_images(tmp_path / "imgs", [50])
    frame = started(ImageFolderCamera(CameraState(), str(folder), simulate_exposure=False)).capture()
    assert frame.dtype == np.uint8 and frame.shape == (6, 8, 3)


def test_single_file_source(tmp_path):
    write_images(tmp_path / "imgs", [77, 99])
    cam = started(ImageFolderCamera(CameraState(), str(tmp_path / "imgs" / "img_1.png"), simulate_exposure=False))
    assert [int(cam.capture().mean()) for _ in range(3)] == [99, 99, 99]


@pytest.mark.parametrize("source", ["empty", "missing"])
def test_empty_or_missing_folder_gives_noise(tmp_path, capsys, source):
    folder = tmp_path / source
    if source == "empty":
        folder.mkdir()
        (folder / "notes.txt").write_text("not an image")
    cam = started(ImageFolderCamera(CameraState(), str(folder), simulate_exposure=False))
    assert "no readable images" in capsys.readouterr().out
    frame = cam.capture()
    assert frame.shape == (256, 256, 3) and frame.std() > 10


def test_unreadable_image_is_skipped(tmp_path):
    folder = write_images(tmp_path / "imgs", [40])
    (folder / "broken.jpg").write_bytes(b"not a jpeg")
    cam = started(ImageFolderCamera(CameraState(), str(folder), simulate_exposure=False))
    assert [int(cam.capture().mean()) for _ in range(2)] == [40, 40]


def test_fast_mode_skips_exposure_wait(tmp_path):
    folder = write_images(tmp_path / "imgs", [1])
    state = CameraState(exposure=2_000_000)  # 2 s
    cam = started(ImageFolderCamera(state, str(folder), simulate_exposure=False))
    t = time.perf_counter()
    cam.capture()
    assert time.perf_counter() - t < 0.5


def test_simulated_exposure_waits(tmp_path):
    folder = write_images(tmp_path / "imgs", [1])
    cam = started(ImageFolderCamera(CameraState(exposure=200_000), str(folder), simulate_exposure=True))
    t = time.perf_counter()
    cam.capture()
    assert time.perf_counter() - t >= 0.19


def test_capturer_queues_one_item_per_capture(tmp_path):
    folder = write_images(tmp_path / "imgs", [5, 6])
    cam = ImageFolderCamera(CameraState(), str(folder), simulate_exposure=False)
    calls = {"n": 0}
    real_capture = cam.capture

    def capture_then_stop():
        calls["n"] += 1
        frame = real_capture()
        if calls["n"] == 3:
            cam.running = False
        return frame

    cam.capture = capture_then_stop
    cam.capturer()
    assert cam.queue.qsize() == 3


def test_repo_test_data_replays():
    cam = started(ImageFolderCamera(CameraState(), TEST_DATA, simulate_exposure=False))
    assert len(cam.paths) >= 1
    assert cam.capture().ndim == 3


def test_legacy_fake_camera_frames():
    frames = [np.full((4, 4, 3), 9, np.uint8)]
    assert int(started(FakeCamera(CameraState(), frames)).capture().mean()) == 9


def test_finder_source_setting_selects_images(tmp_path):
    folder = write_images(tmp_path / "custom", [123])
    settings = Settings.model_validate({"runtime": {"profile": "sim"},
                                        "finder_camera": {"source": str(folder), "simulate_exposure": False}})
    chosen = backends.resolve_backends(settings)
    cam = started(backends.build("finder_camera", chosen["finder_camera"], ObservationContext(), settings))
    assert int(cam.capture().mean()) == 123


# ---------- imaging camera ----------
def test_imaging_from_images_brightness_follows_exposure(tmp_path):
    folder = write_images(tmp_path / "scene", [40])
    cam = FakeImagingCamera(source=str(folder), seed=1)
    cam.connect()
    cam.configure(100_000, 0)
    short = cam.capture().mean()
    cam.configure(200_000, 0)
    long = cam.capture().mean()
    assert long > short
    assert short == pytest.approx(40, abs=2) and long == pytest.approx(80, abs=2)


def test_imaging_from_images_saturates(tmp_path):
    folder = write_images(tmp_path / "scene", [200])
    cam = FakeImagingCamera(source=str(folder), seed=1)
    cam.connect()
    cam.configure(1_000_000, 0)
    assert cam.capture().max() == 255


def test_imaging_from_images_keeps_image_shape(tmp_path):
    folder = write_images(tmp_path / "scene", [40])
    cam = FakeImagingCamera(source=str(folder), seed=1)
    cam.connect()
    cam.configure(100_000, 0)
    assert cam.capture().shape == (6, 8, 3)


def test_imaging_from_images_unplug_and_reconnect(tmp_path):
    cam = FakeImagingCamera(source=str(write_images(tmp_path / "scene", [40])), seed=1)
    assert cam.connect()
    cam.present = False
    assert not cam.is_connected() and cam.capture() is None
    cam.present = True
    assert cam.connect() and cam.capture() is not None


def test_imaging_seed_is_deterministic():
    a, b = FakeImagingCamera(seed=7), FakeImagingCamera(seed=7)
    for cam in (a, b):
        cam.connect()
        cam.configure(10_000, 0)
    assert np.array_equal(a.capture(), b.capture())
