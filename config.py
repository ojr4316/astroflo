""" Persistent device settings (settings.json), editable from the web UI """
import json
import os
import threading
from typing import Literal, Optional
from pydantic import BaseModel, Field
from utils import BASE_DIR

settings_file = os.path.join(BASE_DIR, "settings.json")
legacy_settings_file = os.path.join(BASE_DIR, "settings.txt")


class OpticsSettings(BaseModel):
    focal_length: float = Field(1200.0, gt=0)
    aperture: float = Field(200.0, gt=0)
    eyepiece: float = Field(25.0, gt=0)
    eyepiece_fov: float = Field(40.0, gt=0)
    zoom: float = Field(1.0, gt=0)


class FinderCameraSettings(BaseModel):
    """ The plate-solving camera (Pi camera) """
    exposure_us: int = Field(600_000, ge=100, le=30_000_000)
    gain: float = Field(16.0, ge=0, le=64)
    fake_image_test: bool = False


class ImagingCameraSettings(BaseModel):
    """ External camera attached to the telescope (main imaging camera) """
    backend: Literal["none", "fake", "alpaca", "uvc"] = "none"
    alpaca_address: str = "127.0.0.1:11111"  # host:port of ASCOM Alpaca server
    alpaca_device: int = Field(0, ge=0)
    uvc_index: int = Field(0, ge=0)  # /dev/videoN for USB / UVC cameras
    exposure_s: float = Field(5.0, ge=0.0001, le=3600)
    gain: int = Field(0, ge=0)
    binning: int = Field(1, ge=1, le=8)
    save_fits: bool = True


class SolverSettings(BaseModel):
    fov: float = Field(21.0, gt=0)


class AlignmentSettings(BaseModel):
    x_offset: float = 0.0
    y_offset: float = 0.0
    view_angle: float = 0.0


class LocationSettings(BaseModel):
    latitude: float = Field(43.1566, ge=-90, le=90)
    longitude: float = Field(-77.6088, ge=-180, le=180)
    elevation: float = 150.0
    min_visible_altitude: float = Field(20.0, ge=-90, le=90)


class DisplaySettings(BaseModel):
    enabled: bool = True
    brightness: float = Field(0.5, ge=0, le=1)


class IntegrationSettings(BaseModel):
    stellarium_enabled: bool = True
    stellarium_port: int = Field(10001, ge=1, le=65535)
    coordinate_logging: bool = False
    sky_drift: bool = True


class CaptureSettings(BaseModel):
    max_kept: int = Field(50, ge=1, le=10_000)


class WebSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(8080, ge=1, le=65535)
    stream_fps: float = Field(2.0, gt=0, le=15)


class Settings(BaseModel):
    optics: OpticsSettings = OpticsSettings()
    finder_camera: FinderCameraSettings = FinderCameraSettings()
    imaging_camera: ImagingCameraSettings = ImagingCameraSettings()
    solver: SolverSettings = SolverSettings()
    alignment: AlignmentSettings = AlignmentSettings()
    location: LocationSettings = LocationSettings()
    display: DisplaySettings = DisplaySettings()
    integrations: IntegrationSettings = IntegrationSettings()
    captures: CaptureSettings = CaptureSettings()
    web: WebSettings = WebSettings()


def _read_legacy(path: str) -> dict:
    """ Migrate old `key: value` settings.txt """
    values = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                k, v = line.split(":", 1)
                try:
                    values[k.strip()] = float(v.strip())
                except ValueError:
                    pass
    optics = {k: values[k] for k in ("aperture", "focal_length", "eyepiece", "eyepiece_fov") if k in values}
    alignment = {k: values[k] for k in ("x_offset", "y_offset", "view_angle") if k in values}
    return {"optics": optics, "alignment": alignment}


def deep_merge(base: dict, update: dict) -> dict:
    out = dict(base)
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class SettingsStore:
    def __init__(self, path: str = settings_file, legacy_path: Optional[str] = legacy_settings_file):
        self.path = path
        self.legacy_path = legacy_path
        self.lock = threading.Lock()
        self.settings = self.load()

    def load(self) -> Settings:
        try:
            if os.path.exists(self.path):
                with open(self.path, encoding="utf-8") as f:
                    return Settings.model_validate(json.load(f))
            if self.legacy_path and os.path.exists(self.legacy_path):
                return Settings.model_validate(_read_legacy(self.legacy_path))
        except Exception as e:
            print(f"Error loading settings, using defaults: {e}")
        return Settings()

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(self.settings.model_dump_json(indent=2))
        os.replace(tmp, self.path)

    def update(self, partial: dict) -> Settings:
        """ Validate + persist a partial update; raises pydantic.ValidationError """
        with self.lock:
            merged = deep_merge(self.settings.model_dump(), partial)
            self.settings = Settings.model_validate(merged)
            self.save()
            return self.settings
