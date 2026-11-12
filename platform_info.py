""" Host platform detection and capability probes. Safe to import on any OS (no hardware imports). """
import importlib.util
import os
import platform
import shutil
import sys

PI_HOSTNAME = "rpi"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_pi() -> bool:
    """ The device is identified by hostname (works on every OS, unlike os.uname) """
    return is_linux() and platform.node() == PI_HOSTNAME


def has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def has_executable(name: str) -> bool:
    return shutil.which(name) is not None


def has_v4l2_ctl() -> bool:
    return is_linux() and has_executable("v4l2-ctl")


def os_name() -> str:
    if is_linux():
        return "Linux"
    if is_macos():
        return "macOS"
    if is_windows():
        return "Windows"
    return sys.platform


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")
