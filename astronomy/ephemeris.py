import numpy as np
import os
from skyfield.api import wgs84, load
from skyfield.positionlib import ICRF

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ephemeris_file = os.path.join(BASE_DIR, "..", "de440s.bsp")
asteroids_file = os.path.join(BASE_DIR, "..", "sb441-n16.bsp")

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

class Ephemeris:
    def __init__(self, lat, lon, elevation, time=None): #
        self.location = wgs84.latlon(lat, lon, elevation)
        self.ephemeris_file = ephemeris_file
        self.planets = load(ephemeris_file)
        self.asteroids = load(asteroids_file)
        self.earth = self.planets["EARTH"]
        self.topocentric = self.earth + self.location
        self.timescale = load.timescale()
        self.names = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO", "SUN", "MOON"]
        self.time = time
        if self.time is None:
            self.time = self.timescale.now()

    def get_planet(self, planet_name: str):
        planet_name = planet_name.upper()
        if f'{planet_name} BARYCENTER' in self.planets:
            return self.planets[f'{planet_name} BARYCENTER']
        return self.planets[planet_name]
    
    def get_current_positions(self):
        positions = {}
        
        for planet_name in self.names:
            positions[planet_name] = self.get_current_position(planet_name)
        
        for target_id in self.asteroids.names():
            if target_id == 10: 
                continue # Skip Sun!
            asteroid_position = self.get_current_position_asteroid(target_id)
            if asteroid_position:
                positions[asteroid_position['Name']] = asteroid_position
        
        return positions
    
    def get_current_position(self, planet_name: str):
        topocentric = self.earth + self.location
        
        try:
            planet = self.get_planet(planet_name)
            geocentric = topocentric.at(self.time).observe(planet).apparent()
            ra, dec, dist = geocentric.radec()
            
            return {
                'Name': planet_name,
                'RAdeg': ra.degrees,
                'DEdeg': dec.degrees,
                'Vmag': self.get_planet_magnitude(planet_name),
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
            obs_pos = self.topocentric.at(self.time).position.km
            sun_pos = self.planets['SUN'].at(self.time).position.km
            asteroid_pos = self.asteroids[target_id].at(self.time).position.km

            pos = sun_pos + (asteroid_pos - obs_pos)

            geocentric = ICRF(pos, center=self.topocentric.center, t=self.time)
            ra, dec, dist = geocentric.radec()

            return {
                'Name': clean(name),
                'RAdeg': ra.degrees,
                'DEdeg': dec.degrees,
                'Vmag': 5.0,
                'is_planet': False
            }
        except Exception as e:
            print(f"Error processing asteroid {name} ({target_id}): {e}")
        
        return None
    
    def get_planet_magnitude(self, planet_name):
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
        return magnitudes.get(planet_name, 5.0)