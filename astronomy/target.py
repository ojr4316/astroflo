from astronomy.stars import Stars
from astropy.coordinates import SkyCoord, EarthLocation, GCRS

from PIL import Image, ImageDraw
import numpy as np
from astronomy.ephemeris import Ephemeris

class TargetManager:

    def __init__(self, location: EarthLocation):
        self.location = location
        self.planets = Ephemeris(
            lat=location.lat.degree, 
            lon=location.lon.degree, 
            elevation=location.height.value
        )
        self.stars = Stars(self.planets)
        
        # Current target information
        self.ra = None
        self.dec = None
        self.name = None

        self.catalog = None
        self.index = 0 
        
        self.distance = 0.0

    def set_target(self, ra: float, dec: float, name: str = None):
        self.ra = ra
        self.dec = dec
        self.name = name
        
    def get_target_position(self):
        if self.ra is None:
            return None
        return (self.ra, self.dec)


    