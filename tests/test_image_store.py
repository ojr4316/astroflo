import os
import datetime
import numpy as np

from capture.image_store import ImageStore, sanitize, timestamp_name


def test_sanitize():
    assert sanitize("M42") == "M42"
    assert sanitize("NGC 224 / Andromeda") == "NGC_224___Andromeda"
    assert sanitize("  ") == "unnamed"
    assert sanitize(None) == "unnamed"
    assert sanitize("..") == "unnamed"


def test_timestamp_name():
    now = datetime.datetime(2026, 11, 11, 21, 4, 5, 123456)
    assert timestamp_name(now) == "2026-11-11_21-04-05-123"


def test_auto_and_manual_directories(tmp_path):
    store = ImageStore(str(tmp_path))
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    now = datetime.datetime(2026, 11, 11, 21, 4, 5, 123000)

    auto = store.save(frame, "M42", now)
    manual = store.save(frame, None, now)

    assert auto == os.path.join(str(tmp_path), "M42", "2026-11-11_21-04-05-123.png")
    assert manual == os.path.join(str(tmp_path), "manual", "2026-11-11_21-04-05-123.png")
    assert os.path.exists(auto) and os.path.exists(manual)


def test_collision_does_not_overwrite(tmp_path):
    store = ImageStore(str(tmp_path))
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    now = datetime.datetime(2026, 11, 11, 21, 4, 5, 123000)

    first = store.save(frame, "M42", now)
    second = store.save(frame, "M42", now)
    third = store.save(frame, "M42", now)

    assert first.endswith("2026-11-11_21-04-05-123.png")
    assert second.endswith("2026-11-11_21-04-05-123_1.png")
    assert third.endswith("2026-11-11_21-04-05-123_2.png")


def test_16bit_grayscale_saved(tmp_path):
    store = ImageStore(str(tmp_path))
    frame = np.full((8, 8), 1000, dtype=np.uint16)
    path = store.save(frame, "M13")
    import cv2
    loaded = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    assert loaded.dtype == np.uint16 and loaded[0, 0] == 1000
