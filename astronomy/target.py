from astronomy.stars import Stars
from astropy.coordinates import EarthLocation
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

    def clear_target(self):
        self.ra = self.dec = self.name = None

    def has_target(self):
        return self.ra is not None and self.dec is not None

    def set_target(self, ra: float, dec: float, name: str = None):
        self.ra = ra
        self.dec = dec
        self.name = name
        
    def get_target_position(self):
        if self.ra is None:
            return None
        return (self.ra, self.dec)


    