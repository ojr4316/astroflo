""" Runtime profile resolution and the hardware backend registry.

Profiles: `pi` (real hardware) and `sim` (simulated hardware, any OS). Each component
(finder camera, imaging camera, solver, display, input) can override the profile
default. Hardware modules are only imported by their factory, so nothing Pi-specific
is imported unless that backend is selected.
"""
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import platform_info
from utils import BASE_DIR

PROFILES = ("pi", "sim")
PROFILE_ENV = "ASTROFLO_PROFILE"
CEDAR_PATH_ENV = "ASTROFLO_CEDAR_PATH"
SNAPSHOT_DIR_ENV = "ASTROFLO_SNAPSHOT_DIR"

PROFILE_DEFAULTS = {
    "pi": {"finder_camera": "rpi", "imaging_camera": "sv105", "solver": "cedar", "display": "tft", "input": "gpio"},
    "sim": {"finder_camera": "images", "imaging_camera": "fake", "solver": "fake", "display": "virtual", "input": "sim"},
}
COMPONENTS = tuple(PROFILE_DEFAULTS["pi"].keys())


class BackendUnavailable(RuntimeError):
    """ A backend was requested that cannot run here (wrong OS, missing package or tool) """


def resolve_profile(setting: str = "auto", override: Optional[str] = None) -> str:
    """ Command-line override, then ASTROFLO_PROFILE env var, then the saved setting, then Pi detection """
    value = (override or os.environ.get(PROFILE_ENV) or setting or "auto").strip().lower()
    if value == "auto":
        return "pi" if platform_info.is_pi() else "sim"
    if value not in PROFILES:
        raise ValueError(f"Unknown astroflo profile '{value}'. Allowed values: auto, {', '.join(PROFILES)}")
    return value


# Checked in order when no path is configured (the last one is the original Pi install location)
CEDAR_DEFAULT_PATHS = (os.path.join(os.path.expanduser("~"), "cedar-solve"), "/home/owen/cedar-solve")


def cedar_path(setting: str = "") -> str:
    path = os.environ.get(CEDAR_PATH_ENV) or setting
    if path:
        return os.path.expanduser(path)
    return next((p for p in CEDAR_DEFAULT_PATHS if os.path.isdir(p)), CEDAR_DEFAULT_PATHS[0])


# ---------- availability checks: return None if usable, else the reason ----------
def _needs_linux_module(*modules: str) -> Callable[..., Optional[str]]:
    def check(**_):
        if not platform_info.is_linux():
            return f"only runs on Linux (this is {platform_info.os_name()})"
        missing = [m for m in modules if not platform_info.has_module(m)]
        return f"missing Python package(s): {', '.join(missing)}" if missing else None
    return check


def _linux_only(**_):
    return None if platform_info.is_linux() else f"only runs on Linux (this is {platform_info.os_name()})"


def _tetra3_check(**_):
    return None if platform_info.has_module("tetra3") else "tetra3 is not installed (pip install -r requirements-solver.txt)"


def _cedar_check(settings=None, **_):
    if not platform_info.is_linux():
        return f"Cedar only runs on Linux/the Pi (this is {platform_info.os_name()})"
    path = cedar_path(settings.runtime.cedar_path if settings is not None else "")
    if not os.path.isdir(os.path.join(path, "tetra3")) and not platform_info.has_module("tetra3.cedar_detect_client"):
        return f"cedar-solve not found at {path} (set {CEDAR_PATH_ENV})"
    return None


def _gpio_check(display: str = None, **_):
    if display != "tft":
        return "GPIO buttons are read through the TFT bonnet; set display to 'tft' or input to 'sim'"
    return None


def _always(**_):
    return None


# ---------- factories ----------
def _resolve_source(source: str) -> str:
    return source if os.path.isabs(source) else os.path.join(BASE_DIR, source)


def _rpi_camera(ctx, settings, **_):
    from capture.rpi_camera import RPiCamera
    return RPiCamera(ctx.camera_state)


def _images_camera(ctx, settings, **_):
    from capture.fake_camera import ImageFolderCamera
    fc = settings.finder_camera
    return ImageFolderCamera(ctx.camera_state, _resolve_source(fc.source), simulate_exposure=fc.simulate_exposure)


def _sv105(ctx, settings, **_):
    from capture.sv105_camera import SV105Camera
    return SV105Camera()


def _fake_imaging(ctx, settings, **_):
    from capture.fake_imaging_camera import FakeImagingCamera
    return FakeImagingCamera()


def _no_imaging(ctx, settings, **_):
    return None


def _fake_solver(ctx, settings, **_):
    from solve.fake_solver import FakeSolver
    rt = settings.runtime
    return FakeSolver(ctx.solver_state, ctx.telescope_state, target=(rt.fake_solve_ra, rt.fake_solve_dec))


def _tetra3_solver(ctx, settings, **_):
    from solve.tetra3_solver import Tetra3Solver
    return Tetra3Solver(ctx.solver_state, ctx.telescope_state)


def _cedar_solver(ctx, settings, **_):
    from solve.cedar import CedarSolver
    return CedarSolver(ctx.solver_state, ctx.telescope_state, cedar_path(settings.runtime.cedar_path))


def _tft(ctx, settings, **_):
    from hardware.tft_display import TFTDisplay
    return TFTDisplay()


def _virtual(ctx, settings, **_):
    from hardware.virtual_display import VirtualDisplay
    return VirtualDisplay(snapshot_dir=os.environ.get(SNAPSHOT_DIR_ENV) or None)


def _gpio_input(ctx, settings, display=None, **_):
    from hardware.sim_input import DisplayButtons
    return DisplayButtons(display)


def _sim_input(ctx, settings, **_):
    from hardware.sim_input import SimInput
    return SimInput()


@dataclass
class Backend:
    factory: Callable[..., Any]
    check: Callable[..., Optional[str]] = _always


REGISTRY: Dict[str, Dict[str, Backend]] = {
    "finder_camera": {"rpi": Backend(_rpi_camera, _needs_linux_module("picamera2")),
                      "images": Backend(_images_camera)},
    "imaging_camera": {"sv105": Backend(_sv105, _linux_only),
                       "fake": Backend(_fake_imaging),
                       "none": Backend(_no_imaging)},
    "solver": {"fake": Backend(_fake_solver),
               "tetra3": Backend(_tetra3_solver, _tetra3_check),
               "cedar": Backend(_cedar_solver, _cedar_check)},
    "display": {"tft": Backend(_tft, _needs_linux_module("board", "digitalio", "adafruit_rgb_display")),
                "virtual": Backend(_virtual)},
    "input": {"gpio": Backend(_gpio_input, _gpio_check),
              "sim": Backend(_sim_input)},
}


def resolve_backends(settings, profile_override: Optional[str] = None) -> Dict[str, str]:
    """ {component: backend name} for these settings; raises BackendUnavailable / ValueError """
    rt = settings.runtime
    profile = resolve_profile(rt.profile, profile_override)
    chosen = {}
    for component in COMPONENTS:
        name = getattr(rt, component)
        chosen[component] = PROFILE_DEFAULTS[profile][component] if name == "auto" else name
    for component, name in chosen.items():
        if name not in REGISTRY[component]:
            raise ValueError(f"Unknown {component} backend '{name}'. Allowed: {', '.join(REGISTRY[component])}")
        reason = REGISTRY[component][name].check(settings=settings, display=chosen["display"])
        if reason:
            raise BackendUnavailable(f"{component} backend '{name}' is not available: {reason}")
    chosen["profile"] = profile
    return chosen


def build(component: str, name: str, ctx, settings, **kwargs):
    return REGISTRY[component][name].factory(ctx, settings, **kwargs)
