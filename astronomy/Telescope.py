import os
import numpy as np
from astronomy.target import TargetManager
from astropy.coordinates import EarthLocation
import astropy.units as u
from starplot.optics import Reflector, Optic
from skyfield.api import wgs84, load
from astronomy.celestial import CelestialObject

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.txt")

rochesterLat = 43.1566
rochesterLong = -77.6088
rochesterElevation = 150

rochester = EarthLocation(
    lat=rochesterLat*u.deg, lon=rochesterLong*u.deg, height=rochesterElevation*u.m)

from utils import is_pi
if is_pi():
    ephemeris = "/home/owen/astroflo/de440s.bsp"
else:
    ephemeris = 'de440s.bsp'
planets = load(ephemeris)
earth = planets["EARTH"]

def get_planet(planet_name: str):
    if f'{planet_name.upper()} BARYCENTER' in planets:
        return planets[f'{planet_name.upper()} BARYCENTER']
    return planets[planet_name.upper()]

class Telescope:
    def __init__(self, aperature: int, focal_length: int, eyepiece: int, eyepiece_fov: int, zoom: int = 1):
        self.aperture = aperature
        self.focal_length = focal_length
        self.eyepiece = eyepiece
        self.eyepiece_fov = eyepiece_fov
        self.zoom = zoom # barlow

        self.position = None
        self.last_position = None
        self.camera_offset = (0, 0)
        self.viewing_angle = 0 # 0-359deg

        self.location = rochester
        self.wgsLocation = wgs84.latlon(rochesterLat, rochesterLong, rochesterElevation) 

        self.target_manager = TargetManager(rochester)
        self.speed = 0
        
        self.timescale = load.timescale()
        self.time = self.timescale.now() #self.timescale.utc(2025, 3, 21, 2, 0, 0)

        self.load_settings()
    
    def get_time(self):
        if self.time is None:
            return self.timescale.now()
        return self.time

    def magnification(self):
        return self.focal_length / self.eyepiece # https://skyandtelescope.org/observing/stargazers-corner/simple-formulas-for-the-telescope-owner/
    
    def true_fov(self):
        return self.eyepiece_fov / self.magnification()

    def get_limiting_magnitude(self):
         # https://www.rocketmime.com/astronomy/Telescope/MagnitudeGain.html

        light_pollution_offset = 1 # TODO: Make this more dynamic or remove. But currently is too generous
        return (2 + 5 * np.log10(self.aperture)) - light_pollution_offset
    
    def optic(self) -> Optic:
        return Reflector(self.focal_length, self.eyepiece, self.eyepiece_fov + 10) # raise to better match stellarium

    def observe_local(self, target) -> CelestialObject:
        target = get_planet(target)
        if target is None:
            raise ValueError(f"Target {target} not found in ephemeris")
        topocentric = earth + self.wgsLocation
        geocentric = topocentric.at(self.get_time()).observe(target).apparent()

        ra, dec, dist = geocentric.radec() # TODO: Analyze whether using time is more accurate
        # If so, implement a system that manually marks planets
        # Starplots current system plots J2000 coordinates, but are slightly off for planets

        local = CelestialObject("Planet", 0, "Planet", "", ra.degrees, dec.degrees, "", False)
        return local


    def set_camera_offset(self, x: float, y: float):
        self.camera_offset = (x, y)
        self.save_settings()

    def get_position(self):
        if self.position is None:
            return None
        return (self.position[0] + self.camera_offset[0], self.position[1] + self.camera_offset[1])
        
    def set_position(self, ra: float, dec: float):
        if self.last_position is not None:
            self.speed = ((ra - self.last_position[0]) ** 2 + (dec - self.last_position[1]) ** 2) ** 0.5
        if self.position is not None:
            self.last_position = self.position
        self.position = (ra, dec)
    
    def modify(self, idx, increase=False): # Telescope Settings Page, TODO: Maybe modify UI interally to adjust values
        match(idx):
            case 0: self.aperture += (1 if increase else -1)
            case 1: self.focal_length += (1 if increase else -1)
            case 2: self.eyepiece += (1 if increase else -1)
            case 3: self.eyepiece_fov += (1 if increase else -1)
        self.save_settings()

    def get_settings(self): # Telescope Settings Page
        return {"aperture": self.aperture, "focal_length": self.focal_length, "eyepiece": self.eyepiece, "eyepiece_fov": self.eyepiece_fov}

    def get_cam_settings(self): # Camera Settings Page
        return {"x_offset": f"{self.camera_offset[0]:.1f}", "y_offset": f"{self.camera_offset[1]:.1f}", "view_angle": f"{self.viewing_angle}"}
    
    def save_settings(self): 
        settings = {**self.get_settings(), **self.get_cam_settings()}
        with open(SETTINGS_FILE, "w") as f:
            for key, value in settings.items():
                f.write(f"{key}: {value}\n")

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            self.save_settings()
            return
        settings = {}
        with open(SETTINGS_FILE, "r") as f:
            for line in f:
                key, value = line.strip().split(": ")
                settings[key] = value
        self.aperture = int(settings["aperture"])
        self.focal_length = int(settings["focal_length"])
        self.eyepiece = int(settings["eyepiece"])
        self.eyepiece_fov = int(settings["eyepiece_fov"])
        self.camera_offset = (float(settings["x_offset"]), float(settings["y_offset"]))
        self.viewing_angle = int(settings["view_angle"])
        print(f"Settings loaded from {SETTINGS_FILE}")

    