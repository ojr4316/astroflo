import time
import threading
from typing import ClassVar
from dataclasses import field
from enum import IntEnum
import numpy as np
from dataclasses import dataclass
from skyfield.api import Time
from astropy.coordinates import EarthLocation
from utils import radec_to_altaz, BASE_DIR
from skyfield.api import wgs84, load
import astropy.units as u
import os
from PIL import Image
from astronomy.stellarium import StellariumConnection
from astropy.time import Time as AstropyTime

# File Locations
offset_file = os.path.join(BASE_DIR, "offset.npy")
coordinate_log = os.path.join(BASE_DIR, "coord_log.txt")

# Observation Location
rochesterLat = 43.1566
rochesterLong = -77.6088
rochesterElevation = 150

@dataclass
class CameraState:
    enabled: bool = False
    exposure: float = 600_000 # microseconds
    gain: float = 16.0
    latest_image: Image = None
    fake_image_test: bool = False

@dataclass
class ImagingState:
    """Shared state for the SV105 imaging camera. Written by the imaging controller, read by the UI."""
    connected: bool = False
    auto_enabled: bool = False
    exposure_us: float = 0.0
    gain: float = 0.0
    target_in_field: bool = False
    frames_saved: int = 0
    last_result: str = ""        # e.g. "Saved", "Failed"
    last_result_time: float = 0.0
    manual_requested: threading.Event = field(default_factory=threading.Event)

    def set_result(self, result: str):
        self.last_result = result
        self.last_result_time = time.time()

@dataclass
class TelescopeState:
    position: tuple = None
    roll: float = 0.0

    logging: bool = False

    stel: StellariumConnection = StellariumConnection()

    def is_solved(self):
        return self.position is not None

    def solve_result(self, coordinates: tuple, roll: float = 0.0):
        self.position = coordinates
        self.roll = roll
        self._log_coordinates()
        self.stel.update_position(coordinates[0], coordinates[1])

    def _log_coordinates(self):
        if self.logging and self.position is not None:
            with open(coordinate_log, "a", encoding="utf-8") as f:
                log = f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} - {self.position}\n"
                f.write(log)

    def sky_drift(self, t=1):
        if self.position == None:
            return
        ra, dec = self.position
        ra_offset = (15 * np.cos(dec)) * t / (60*60) # Sky Drift, scaled by time, to hours
        new_ra = ra + ra_offset
        self.position = (new_ra, dec)

@dataclass
class TelescopeOptics:
    focal_length: float = 1200.0 # All measured in mm
    aperture: float = 200.0
    eyepiece: float = 25.0
    eyepiece_fov: float = 40.0 # Apparent field of view in degrees of eyepiece
    zoom: float = 1.0 # Represent zoom eyepiece or Barlow lens

    def magnification(self):
        return self.focal_length / self.eyepiece # https://skyandtelescope.org/observing/stargazers-corner/simple-formulas-for-the-telescope-owner/
    
    def get_limiting_magnitude(self):
         # https://www.rocketmime.com/astronomy/Telescope/MagnitudeGain.html
        limiting_magnitude = (2 + 5 * np.log10(self.aperture))
        light_pollution_offset = 1 # TODO: Make this more dynamic or remove. But currently is too generous
        return limiting_magnitude - light_pollution_offset - (self.zoom/3)
    
    def field_radius(self):
        fov = self.eyepiece_fov / self.magnification()
        return (fov / 2) * self.zoom

def load_target_pixel():
    if os.path.exists(offset_file):
        offsets = np.load(offset_file)
        return offsets
    return None

@dataclass
class SolverState:
    fov: float = 21.0
    target_pixel: ClassVar[tuple] = load_target_pixel()
    last_solved: float = time.time()
    
    def save_offset(self, offset):
        self.target_pixel = offset
        np.save(offset_file, offset)


class CatalogType(IntEnum):
    STARS = 0
    DSOS = 1
    SOLAR = 2

@dataclass
class TargetState:
    name: str = ""
    ra: float = None
    dec: float = None
    catalog_filter: CatalogType = CatalogType.STARS

    def has_target(self):
        return self.ra is not None and self.dec is not None

    def set_target(self, ra: float, dec: float, name: str = None):
        self.ra = ra
        self.dec = dec
        self.name = name


@dataclass
class Environment:
    timescale = load.timescale()
    time: Time = timescale.now()
    min_visible_altitude: float = 20.0
    astropy_location = EarthLocation(lat=rochesterLat*u.deg, lon=rochesterLong*u.deg, height=rochesterElevation*u.m)
    skyfield_location = wgs84.latlon(rochesterLat, rochesterLong, rochesterElevation)

    def astropy_time(self):
        return AstropyTime(self.time.tt, format='jd', scale='tt')
    
    def set_location(self, lat: float, lon: float, elevation: float):
        self.astropy_location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=elevation*u.m)
        self.skyfield_location = wgs84.latlon(lat, lon, elevation)

    def is_target_visible(self, ra: float, dec: float):
        alt, az = radec_to_altaz(ra, dec, self.astropy_time(), self.astropy_location)
        return alt > self.min_visible_altitude

class ObservationContext:
    def __init__(self):
        self.environment = Environment()
        self.camera_state = CameraState()
        self.imaging_state = ImagingState()
        self.telescope_state = TelescopeState()
        self.telescope_optics = TelescopeOptics()
        self.solver_state = SolverState()
        self.target_state = TargetState()
        self.lock = threading.RLock() # Guards writes coming from the web server

    def apply_settings(self, settings):
        """ Push a config.Settings into the live state objects """
        with self.lock:
            o = settings.optics
            self.telescope_optics.focal_length = o.focal_length
            self.telescope_optics.aperture = o.aperture
            self.telescope_optics.eyepiece = o.eyepiece
            self.telescope_optics.eyepiece_fov = o.eyepiece_fov
            self.telescope_optics.zoom = o.zoom

            self.camera_state.exposure = settings.finder_camera.exposure_us
            self.camera_state.gain = settings.finder_camera.gain
            self.camera_state.fake_image_test = settings.finder_camera.fake_image_test
            self.solver_state.fov = settings.solver.fov
            self.telescope_state.logging = settings.integrations.coordinate_logging

            loc = settings.location
            self.environment.set_location(loc.latitude, loc.longitude, loc.elevation)
            self.environment.min_visible_altitude = loc.min_visible_altitude