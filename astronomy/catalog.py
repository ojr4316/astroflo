import time
import os
import numpy as np
from utils import BASE_DIR, is_within_radius, radec_to_altaz
from astropy.table import Table
from skyfield.api import load
from observation_context import Environment
from skyfield.positionlib import ICRF

catalog_file = os.path.normpath(os.path.join(BASE_DIR, 'data', 'tyc.fits'))
ephemeris_file = os.path.join(BASE_DIR, 'data', "de440s.bsp")
asteroids_file = os.path.join(BASE_DIR, 'data', "sb441-n16.bsp")
PLANET_NAMES = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO", "SUN", "MOON"]

def clean(n) -> str:
    if isinstance(n, list):
        if len(n) > 0:
            n = n[0]
        else:
            return ''
        
    if n is np.ma.masked:
        return ''
    n = str(n)
    n = n.strip()
    n = n[0].upper() + n[1:]
    return n.lower()

def get_planet_magnitude(planet_name):
    magnitudes = {
        'MERCURY': 0.0,
        'VENUS': -4.0,
        'MARS': 0.5,
        'JUPITER': -2.5,
        'SATURN': 0.5,
        'URANUS': 5.5,
        'NEPTUNE': 8.0,
        'PLUTO': 14.0,
        'SUN': -26.8,
        'MOON': -12.6
    }
    return magnitudes.get(planet_name, 7.0)

def load_stars():
    try:
        print("Loading Tycho catalog...", end=' ')
        start = time.time()
        stars = Table.read(catalog_file)
        print(f"Done in {time.time() - start:.2f} seconds")
        return stars
    except Exception as e:
        print(f"Error loading stars catalog: {e}")
        return []

class Catalog:

    def __init__(self, env: Environment):
        self.env = env
        
        self.load()
        self.setup()
    
    def load(self):
        self.stars: Table = load_stars()
        self.planets: dict = load(ephemeris_file)
        self.asteroids: dict = load(asteroids_file)

    def setup(self):
        self.earth = self.planets["EARTH"]
        self.topocentric = self.earth + self.env.skyfield_location
        self.planet_cache = {}
        self.cache_time = None
        self.cache_duration = 3

    def search_by_name(self, n: str): # only for dsos
        n = clean(n)
        name_col = self.stars['Name'].filled('')
        name_strings = np.array([clean(n) for n in name_col])

        results = self.stars[name_strings == n]
        return results

    def search_by_coordinate(self, ra: float, dec: float, radius: float = 0.05, mag_limit: float = 13): # FOV in degrees
        within_radius = is_within_radius(ra, dec, self.stars['RAdeg'], self.stars['DEdeg'], radius)
        star_results = self.stars[within_radius]
        star_results = star_results[star_results['Vmag'] <= mag_limit]

        planets_in_fov = self.get_planets_in_fov(ra, dec, radius)
        return self.build_targets(star_results, planets_in_fov)
    
    def build_targets(self, stars, ephem):
        combined = []
        for star in stars:
            is_planet = False
            if star['TYC'] is not None and str(star['TYC'])[0] == 'M':
                is_planet = True # DSOs
            name = str(star['Name'])
            if len(str(name).replace("-", "")) == 0:
                name = str(star['TYC'])
            combined.append({
                'Name': name,
                'RAdeg': star['RAdeg'],
                'DEdeg': star['DEdeg'],
                'Vmag': star['Vmag'],
                'is_planet': is_planet
            })
            
        for planet in ephem:
            combined.append(planet)
        return combined

    def here(self):
        return self.topocentric.at(self.env.time)

    def get_planet(self, planet_name: str):
        planet_name = planet_name.upper()
        if f'{planet_name} BARYCENTER' in self.planets:
            return self.planets[f'{planet_name} BARYCENTER']
        return self.planets[planet_name]
    
    def get_current_positions(self):
        positions = {}
        
        for planet_name in PLANET_NAMES:
            positions[planet_name] = self.get_current_position(planet_name)
        
        for target_id in self.asteroids.names():
            if target_id == 10: 
                continue # Skip Sun!
            asteroid_position = self.get_current_position_asteroid(target_id)
            if asteroid_position:
                positions[asteroid_position['Name']] = asteroid_position
        
        return positions
    
    def get_current_position(self, planet_name: str):
        try:
            planet = self.get_planet(planet_name)
            geocentric = self.here().observe(planet).apparent()
            ra, dec, dist = geocentric.radec()
            
            return {
                'Name': planet_name,
                'RAdeg': ra.degrees,
                'DEdeg': dec.degrees,
                'Vmag': get_planet_magnitude(planet_name),
                'is_planet': True
            }
        except KeyError:
            print("failed to load ", planet_name)
                
        return {}
    
    def get_current_position_asteroid(self, target_id):
        if target_id not in self.asteroids.names():
            return None
        
        name = self.asteroids.names()[target_id]
        if name is None or clean(name) == '':
            return None
        
        try:
            obs_pos = self.here().position.km
            sun_pos = self.planets['SUN'].at(self.env.time).position.km
            asteroid_pos = self.asteroids[target_id].at(self.env.time).position.km

            pos = sun_pos + (asteroid_pos - obs_pos)

            geocentric = ICRF(pos, center=self.topocentric.center, t=self.env.time)
            ra, dec, dist = geocentric.radec()

            return {
                'Name': clean(name),
                'RAdeg': ra.degrees,
                'DEdeg': dec.degrees,
                'Vmag': 7.0,
                'is_planet': False
            }
        except Exception as e:
            print(f"Error processing asteroid {name} ({target_id}): {e}")
        
        return None

    def get_planets_in_fov(self, ra, dec, radius):
        current_time = time.time()
        
        # Check planet cache
        if (self.cache_time is None or 
            current_time - self.cache_time > self.cache_duration or
            not self.planet_cache):

            self.planet_cache = self.get_current_positions()
            self.cache_time = current_time

        # Filter planets within FOV
        planets_in_fov = []
        
        for planet_name, planet_data in self.planet_cache.items():
            if is_within_radius(ra, dec, planet_data['RAdeg'], planet_data['DEdeg'], radius):
                planets_in_fov.append(planet_data)
        
        return planets_in_fov

    def get_bright_stars(self, mag_limit=6):
        tycho = self.stars
        stars = tycho[(tycho['Vmag'] <= mag_limit) & (tycho['Name'].filled('') != '') & (tycho['TYC'][0] != 'M')]
        targets = self.build_targets(stars, [])
        ra_values = [target['RAdeg'] for target in targets]
        dec_values = [target['DEdeg'] for target in targets]
        alts, azs = radec_to_altaz(ra_values, dec_values, self.env.astropy_time(), self.env.astropy_location)

        mask = alts > self.env.min_visible_altitude
        targets = [targets[i] for i in range(len(targets)) if mask[i]]

        return targets
    
    def get_dsos(self, mag_limit=15):
        tycho = self.stars
        dsos = tycho[(tycho['Vmag'] <= mag_limit) & (np.char.startswith(tycho['TYC'].astype(str), 'M'))]
        targets = self.build_targets(dsos, [])
        ra_values = [target['RAdeg'] for target in targets]
        dec_values = [target['DEdeg'] for target in targets]
        alts, azs = radec_to_altaz(ra_values, dec_values, self.env.astropy_time(), self.env.astropy_location)
        mask = alts > self.env.min_visible_altitude
        targets = [targets[i] for i in range(len(targets)) if mask[i]]

        return targets

    def get_solar_system(self):
        positions_dict = self.get_current_positions()
        
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
        
        targets = self.build_targets([], targets_list)

        ra_values = [target['RAdeg'] for target in targets]
        dec_values = [target['DEdeg'] for target in targets]
        alts, azs = radec_to_altaz(ra_values, dec_values, self.env.astropy_time(), self.env.astropy_location)

        mask = alts > self.env.min_visible_altitude
        targets = [targets[i] for i in range(len(targets)) if mask[i]]

        return targets