from astronomy.catalog import CatalogLoader, CelestialObject, get_apparent_radec
from astropy.coordinates import SkyCoord, EarthLocation, GCRS

class TargetManager:

    def __init__(self, location: EarthLocation):
        self.location = location
        self.catalog_loader = CatalogLoader()

        self.target = None

        self.catalog = None
        self.index = 0 
    
    def get_target_position(self):
        if self.target is None:
            return None
        return get_apparent_radec(self.target.ra, self.target.dec, self.location)
    
    def get_catalog(self):
        return [a.messier_id or a.ngc_id for a in self.catalog_loader.all[self.catalog]]
    