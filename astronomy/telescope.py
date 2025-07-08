import os
import numpy as np
from astronomy.target import TargetManager
from astropy.coordinates import EarthLocation
import astropy.units as u
from starplot.optics import Reflector, Optic
from skyfield.api import wgs84, load
from astronomy.settings import TelescopeSettings
from astronomy.renderer import NavigationStarfield
from operation import OperationManager

rochesterLat = 43.1566
rochesterLong = -77.6088
rochesterElevation = 150
rochester = EarthLocation(
    lat=rochesterLat*u.deg, lon=rochesterLong*u.deg, height=rochesterElevation*u.m)


class Telescope:
    def __init__(self, aperature: int, focal_length: int, eyepiece: int, eyepiece_fov: int, zoom: int = 2):
        self.aperture = aperature
        self.focal_length = focal_length
        self.eyepiece = eyepiece
        self.eyepiece_fov = eyepiece_fov
        self.zoom = zoom # barlow

        self.mount_position = None # RA/DEC camera position
        self.position = None # RA/DEC offset by camera
        self.last_position = None
        self.camera_offset = (0, 0)
        self.viewing_angle = 0 # 0-359deg

        # above settings managed by TelescopeSettings
        self.settings = TelescopeSettings(self)

        self.location = rochester

        self.target_manager = TargetManager(rochester)
        self.renderer = NavigationStarfield(self)
        self.speed = 0
        
        self.timescale = load.timescale()
        self.time = self.timescale.now() #self.timescale.utc(2025, 3, 21, 2, 0, 0)
        
    def set_time(self, time):
        self.time = self.timescale.utc(time)

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

    def set_camera_offset(self, x: float, y: float):
        self.camera_offset = (x, y)
        self.settings.save()

    def get_position(self):
        return self.position
        
    def solve_result(self, ra: float, dec: float):
        self.mount_position = (ra, dec)
        ra += self.camera_offset[0]
        dec += self.camera_offset[1]

        if self.last_position is not None:
            self.speed = ((ra - self.last_position[0]) ** 2 + (dec - self.last_position[1]) ** 2) ** 0.5
        if self.position is not None:
            self.last_position = self.position

        self.position = (ra, dec)
        if OperationManager.log_coordinates:
            self.settings.save_coord()

    def modify(self, idx, increase=False): # Telescope Settings Page, TODO: Maybe modify UI interally to adjust values
        match(idx):
            case 0: self.aperture += (1 if increase else -1)
            case 1: self.focal_length += (1 if increase else -1)
            case 2: self.eyepiece += (1 if increase else -1)
            case 3: self.eyepiece_fov += (1 if increase else -1)
        self.settings.save()

    def sky_drift(self, t=1):
        if self.position == None:
            return
        ra, dec = self.position # edit raw position without cam offset
        ra_offset = (15 * np.cos(dec)) * t / 240 # Sky Drift, scaled by time, to hours
        new_ra = ra + ra_offset
        self.position = (new_ra, dec)
        
