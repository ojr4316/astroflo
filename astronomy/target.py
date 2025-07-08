from astronomy.stars import Stars
from astropy.coordinates import SkyCoord, EarthLocation, GCRS

from PIL import Image, ImageDraw
import numpy as np

# TODO: move/combine ephem

class TargetManager:

    def __init__(self, location: EarthLocation, cam_offset):
        self.location = location
        self.stars = Stars()

        self.ra = None
        self.dec = None
        self.name = None

        self.catalog = None
        self.index = 0 
        
        self.distance = 0.0
        self.cam_offset = cam_offset

    
    def set_target(self, ra: float, dec: float, name: str = None):
        self.ra = ra
        self.dec = dec
        self.name = name
        
    def get_target_position(self):
        if self.ra is None:
            return None
        return (self.ra - self.cam_offset[0], self.dec - self.cam_offset[1])  #get_apparent_radec(self.target.ra, self.target.dec, self.location)


    