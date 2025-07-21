import numpy as np
from astronomy.target import TargetManager
from astropy.coordinates import EarthLocation
import astropy.units as u
from skyfield.api import load
from astronomy.settings import TelescopeSettings
from astronomy.renderer import NavigationStarfield
from operation import OperationManager
from utils import apply_rotation, solve_rotation, radec_to_altaz, altaz_to_radec
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OFFSET_FILE = os.path.join(BASE_DIR, "..", "offset.npy")

rochesterLat = 43.1566
rochesterLong = -77.6088
rochesterElevation = 150
rochester = EarthLocation(
    lat=rochesterLat*u.deg, lon=rochesterLong*u.deg, height=rochesterElevation*u.m)


class Telescope:
    def __init__(self, aperture: int, focal_length: int, eyepiece: int, eyepiece_fov: int, zoom: int = 1):
        self.aperture = aperture
        self.focal_length = focal_length
        self.eyepiece = eyepiece
        self.eyepiece_fov = eyepiece_fov
        self.zoom = zoom # barlow

        self.mount_position = None # RA/DEC camera position
        self.position = None # RA/DEC offset by camera
        self.last_position = None
        self.camera_offset = None
        self.rotation_matrix = None

        self.viewing_angle = 0 # 0-359deg, oriented towards NORTH

        # above settings managed by TelescopeSettings
        self.settings = TelescopeSettings(self)

        self.location = rochester

        self.target_manager = TargetManager(rochester)
        self.renderer = NavigationStarfield(self)
        self.speed = 0
        
        self.timescale = load.timescale()
        self.time = self.timescale.now() #self.timescale.utc(2025, 3, 21, 2, 0, 0)

        if os.path.exists(OFFSET_FILE):
            print("loading previously set offsets")
            offsets = np.load(OFFSET_FILE)
            print(offsets)
            self.rotation_matrix = offsets
    
    def set_rotation_matrix(self, matrix):
        self.rotation_matrix = matrix
        np.save(OFFSET_FILE, matrix)

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
        return (2 + 5 * np.log10(self.aperture)) - light_pollution_offset - (self.zoom/4)
    
    def set_camera_offset(self, x: float, y: float):
        self.camera_offset = (x, y)
        self.settings.save()

    def get_position(self):
        return self.position
        
    def solve_result(self, ra: float, dec: float, roll: float = 0):
        self.mount_position = (ra, dec)
        self.viewing_angle = roll
        if self.rotation_matrix is not None:
            ra, dec = apply_rotation(self.rotation_matrix, ra, dec, roll)
        if self.camera_offset is not None:
            alt, az = radec_to_altaz(ra, dec, self.get_time(), self.location)
            alt += self.camera_offset[1]
            az += self.camera_offset[0]
            ra, dec = altaz_to_radec(alt, az, self.get_time(), self.location)

        if self.last_position is not None:
            self.speed = ((ra - self.last_position[0]) ** 2 + (dec - self.last_position[1]) ** 2) ** 0.5
        if self.position is not None:
            self.last_position = self.position

        self.position = (ra, dec)
        if OperationManager.log_coordinates:
            self.settings.save_coord()

    def sky_drift(self, t=1):
        if self.position == None:
            return
        ra, dec = self.position # edit raw position without cam offset
        ra_offset = (15 * np.cos(dec)) * t / (60*60) # Sky Drift, scaled by time, to hours
        new_ra = ra + ra_offset
        self.position = (new_ra, dec)
    
    def offset_to_brightest(self, min_mag=6, fov_multiplier=10) -> bool:
        if self.mount_position is None:
            print("FAIL: Telescope position is not set")
            return False
        ra, dec = self.mount_position
        alt, az = radec_to_altaz(ra, dec, self.get_time(), self.location)
        roll = self.viewing_angle

        stars = self.target_manager.stars
        r = stars.radius_from_telescope(self.focal_length, self.eyepiece, self.eyepiece_fov) * fov_multiplier
        nearby = stars.search_by_coordinate(ra=ra, dec=dec, radius=r)
        if len(nearby) == 0:
            print("FAIL: No nearby stars")
            return False
        else:
            brightest = nearby[0]
            for s in nearby:
                if s['Vmag'] < brightest['Vmag']: # TODO: fix for negative amgs
                    brightest = s
            
            if brightest['Vmag'] > min_mag:
                print("FAIL: No bright star nearby")
                return False

            tra, tdec = brightest['RAdeg'], brightest['DEdeg']
            talt, taz = radec_to_altaz(tra, tdec, self.get_time(), self.location)

            
            x_offset = taz - az
            y_offset = talt - alt

            self.set_camera_offset(x_offset, y_offset)

            #rotation_matrix = solve_rotation((ra, dec), (tra, tdec), roll)
            #self.set_rotation_matrix(rotation_matrix)

            print(f"Offsetting position to brightest nearby: {brightest['Name']} at RA: {tra}, DEC: {tdec}")
            print(f"Current position: RA: {ra}, DEC: {dec}")
            print("Found offsets:", x_offset, y_offset)

            return True
            
