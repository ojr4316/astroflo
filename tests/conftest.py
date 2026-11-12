""" Shared test setup: platform/hardware markers with conditional skips, and isolation fixtures.

Tests assume NO camera, display or Pi is attached. Hardware tests only run when
ASTROFLO_HW_TESTS=1 is set and the hardware is detected (see `requires_camera`).
"""
import os
import sys

# Allow `import capture...` etc. from the project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("MPLBACKEND", "Agg")  # headless matplotlib on every OS

import numpy as np  # noqa: E402
import pytest  # noqa: E402

import platform_info  # noqa: E402

EPHEMERIS_FILE = os.path.join(ROOT, "data", "de440s.bsp")


def _finder_camera_present() -> bool:
    return platform_info.is_pi() and platform_info.has_module("picamera2")


def _imaging_camera_present() -> bool:
    if not platform_info.is_linux():
        return False
    from capture import v4l2_util
    return v4l2_util.find_device() is not None


def _tft_reason(marker):
    if not platform_info.env_flag("ASTROFLO_HW_TESTS"):
        return "requires TFT bonnet (set ASTROFLO_HW_TESTS=1 with hardware attached)"
    ok = platform_info.is_pi() and all(platform_info.has_module(m) for m in ("board", "digitalio", "adafruit_rgb_display"))
    return None if ok else "requires TFT bonnet (not detected)"


def _camera_reason(kind: str):
    """ None if the camera can be used, else a skip reason """
    if not platform_info.env_flag("ASTROFLO_HW_TESTS"):
        return f"requires {kind} camera (set ASTROFLO_HW_TESTS=1 with hardware attached)"
    present = _finder_camera_present() if kind == "finder" else _imaging_camera_present()
    return None if present else f"requires {kind} camera (not detected)"


# marker -> (description, callable(marker) returning a skip reason or None)
MARKERS = {
    "linux_only": ("test needs Linux", lambda m: None if platform_info.is_linux() else "requires Linux"),
    "macos_only": ("test needs macOS", lambda m: None if platform_info.is_macos() else "requires macOS"),
    "windows_only": ("test needs Windows", lambda m: None if platform_info.is_windows() else "requires Windows"),
    "pi_only": ("test needs the Raspberry Pi", lambda m: None if platform_info.is_pi() else "requires Raspberry Pi"),
    "requires_camera": ("requires_camera('finder'|'imaging'): test needs real camera hardware",
                        lambda m: _camera_reason(m.args[0] if m.args else "finder")),
    "requires_tft": ("test needs the Adafruit TFT bonnet", _tft_reason),
    "requires_v4l2": ("test needs Linux v4l2-ctl",
                      lambda m: None if platform_info.has_v4l2_ctl() else "requires v4l2-ctl (Linux, v4l-utils)"),
    "requires_tetra3": ("test needs the tetra3 package",
                        lambda m: None if platform_info.has_module("tetra3") else "requires tetra3 (requirements-solver.txt)"),
    "requires_ephemeris": ("test needs data/de440s.bsp",
                           lambda m: None if os.path.exists(EPHEMERIS_FILE) else "requires data/de440s.bsp ephemeris"),
    "slow": ("slow test (deselect with -m 'not slow')", lambda m: None),
}


def pytest_configure(config):
    for name, (desc, _) in MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {desc}")


def skip_reason(item):
    for name, (_, check) in MARKERS.items():
        for marker in item.iter_markers(name):
            reason = check(marker)
            if reason:
                return reason
    return None


def pytest_collection_modifyitems(config, items):
    for item in items:
        reason = skip_reason(item)
        if reason:
            item.add_marker(pytest.mark.skip(reason=reason))


@pytest.fixture(scope="session")
def star_table():
    """ The Tycho catalog table (large FITS file): loaded once per test session """
    from astronomy import catalog
    return catalog.load_stars()


@pytest.fixture
def catalog(star_table, monkeypatch):
    """ Real star catalog; planets follow whether data/de440s.bsp is present """
    from astronomy import catalog as catalog_mod
    from observation_context import Environment
    monkeypatch.setattr(catalog_mod, "load_stars", lambda: star_table)
    return catalog_mod.Catalog(Environment())


@pytest.fixture
def sim_ui(catalog, monkeypatch, tmp_path):
    """ Full UIManager on the virtual display with simulated buttons, no page-change debounce """
    from astronomy.starfield import StarfieldRenderer
    from hardware.sim_input import SimInput
    from hardware.state import UIState
    from hardware.ui import UIManager
    from hardware.virtual_display import VirtualDisplay
    from observation_context import ObservationContext

    monkeypatch.setattr(UIState, "debounce_s", 0)
    ctx = ObservationContext()
    catalog.env = ctx.environment
    starfield = StarfieldRenderer(catalog=catalog, telescope_state=ctx.telescope_state,
                                  telescope_optics=ctx.telescope_optics, target_state=ctx.target_state)
    display = VirtualDisplay(snapshot_dir=str(tmp_path / "snapshots"), snapshot_interval_s=0)
    ui = UIManager(ctx, starfield, display=display, buttons=SimInput())
    yield ui
    ui.stop()
    from hardware import renderer
    renderer.status_provider = None


@pytest.fixture(autouse=True)
def seeded_rng():
    np.random.seed(1234)


@pytest.fixture(autouse=True)
def isolated_files(tmp_path, monkeypatch):
    """ Keep tests from writing tracked/device files in the repo (settings, offsets, logs, captures, saves) """
    import config
    import observation_context
    from capture import camera, image_store

    files = tmp_path / "astroflo"
    files.mkdir()
    monkeypatch.setattr(config, "settings_file", str(files / "settings.json"))
    monkeypatch.setattr(config, "legacy_settings_file", str(files / "settings.txt"))
    monkeypatch.setattr(observation_context, "offset_file", str(files / "offset.npy"))
    monkeypatch.setattr(observation_context, "coordinate_log", str(files / "coord_log.txt"))
    monkeypatch.setattr(camera, "BASE_DIR", str(files))
    monkeypatch.setattr(image_store, "DEFAULT_SAVE_DIR", str(files / "saves"))
    monkeypatch.delenv("ASTROFLO_PROFILE", raising=False)
    return files
