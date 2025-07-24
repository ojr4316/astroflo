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
from astropy.time import Time

rochesterLat = 43.1566
rochesterLong = -77.6088
rochesterElevation = 150
rochester = EarthLocation(
    lat=rochesterLat*u.deg, lon=rochesterLong*u.deg, height=rochesterElevation*u.m)

MIN_ALT = 20

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

        

    def astropy_time(self):
        return Time(self.get_time().tt, format='jd', scale='tt')

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
        return (2 + 5 * np.log10(self.aperture)) - light_pollution_offset - (self.zoom/3)
    
    def set_camera_offset(self, x: float, y: float):
        self.camera_offset = (x, y)
        self.settings.save()

    def get_position(self):
        return self.position
        
    def solve_result(self, ra: float, dec: float, roll: float = 0):
        self.mount_position = (ra, dec)
        self.viewing_angle = roll

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
    
    def get_bright_stars(self, mag_limit=6):
        tycho = self.target_manager.stars.tycho
        stars = tycho[(tycho['Vmag'] <= mag_limit) & (tycho['Name'].filled('') != '') & (tycho['TYC'][0] != 'M')]
        targets = self.target_manager.stars.build_targets(stars, [])
        ra_values = [target['RAdeg'] for target in targets]
        dec_values = [target['DEdeg'] for target in targets]
        alts, azs = radec_to_altaz(ra_values, dec_values, self.astropy_time(), self.location)

        mask = alts > MIN_ALT
        targets = [targets[i] for i in range(len(targets)) if mask[i]]

        return targets
    
    def get_dsos(self, mag_limit=15):
        tycho = self.target_manager.stars.tycho
        dsos = tycho[(tycho['Vmag'] <= mag_limit) & (np.char.startswith(tycho['TYC'].astype(str), 'M'))]
        targets = self.target_manager.stars.build_targets(dsos, [])
        ra_values = [target['RAdeg'] for target in targets]
        dec_values = [target['DEdeg'] for target in targets]
        alts, azs = radec_to_altaz(ra_values, dec_values, self.astropy_time(), self.location)
        mask = alts > MIN_ALT
        targets = [targets[i] for i in range(len(targets)) if mask[i]]

        return targets

    def get_solar_system(self):
        positions_dict = self.target_manager.ephemeris.get_current_positions()
        
        # Convert dictionary to list of dictionaries
        if isinstance(positions_dict, dict):
            targets_list = []
            for name, data in positions_dict.items():
                planet_dict = {
                    'Name': name,
                    'RAdeg': data['RAdeg'],
                    'DEdeg': data['DEdeg'],
                    'Vmag': data.get('Vmag', 5.0),  # Default magnitude if not provided
                    'is_planet': True
                }
                targets_list.append(planet_dict)
        else:
            targets_list = positions_dict  # Already a list
        
        targets = self.target_manager.stars.build_targets([], targets_list)

        ra_values = [target['RAdeg'] for target in targets]
        dec_values = [target['DEdeg'] for target in targets]
        alts, azs = radec_to_altaz(ra_values, dec_values, self.astropy_time(), self.location)

        mask = alts > MIN_ALT
        targets = [targets[i] for i in range(len(targets)) if mask[i]]

        return targets

