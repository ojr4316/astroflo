from astropy.table import Table
import numpy as np
import time
import matplotlib
import matplotlib.pyplot as plt
import os
from utils import plt_to_img
import threading
from skyfield.api import wgs84, load
from PIL import Image, ImageDraw

def clean(n) -> str:
    if n is np.ma.masked:
        return ''
    n = str(n)
    n = n.strip()
    return n.lower()

class Ephemeris:
    def __init__(self, lat, lon, elevation, ephemeris_file='de440s.bsp'): #"/home/owen/astroflo/de440s.bsp"
        self.location = wgs84.latlon(lat, lon, elevation)
        self.planets = load(ephemeris_file)
        self.earth = self.planets["EARTH"]
        self.timescale = load.timescale()
        self.names = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO", "SUN", "MOON"]
        self.time = self.timescale.utc(2025, 7, 9, 5, 0, 0)
        
    def get_planet(self, planet_name: str):
        planet_name = planet_name.upper()
        if f'{planet_name} BARYCENTER' in self.planets:
            return self.planets[f'{planet_name} BARYCENTER']
        return self.planets[planet_name]
    
    def get_current_positions(self, current_time=None):
        positions = {}
        
        for planet_name in self.names:
            positions[planet_name] = self.get_current_position(planet_name, current_time)
        
        return positions
    
    def get_current_position(self, planet_name: str, current_time=None):
        if self.time is not None:
            current_time = self.time
        if current_time is None:
            current_time = self.timescale.now()
        
        topocentric = self.earth + self.location
        
        try:
            planet = self.get_planet(planet_name)
            geocentric = topocentric.at(current_time).observe(planet).apparent()
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