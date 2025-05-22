import csv
import os
from typing import List, Optional, Dict
from pathlib import Path
from astropy.coordinates import SkyCoord, EarthLocation, GCRS
from astropy.time import Time
import astropy.units as u

from astronomy.celestial import CelestialObject

def get_apparent_radec(ra_hours: float, dec_deg: float, location: EarthLocation,
                       time_utc: str = None):
    ra_deg = ra_hours * 15

    j2000 = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')
    time = Time(time_utc) if time_utc else Time.now()

    obsgeoloc, obsgeovel = location.get_gcrs_posvel(time)
    gcrs = j2000.transform_to(GCRS(obstime=time, obsgeoloc=obsgeoloc, obsgeovel=obsgeovel))
    apparent = SkyCoord(ra=gcrs.ra, dec=gcrs.dec, frame='icrs')

    return (apparent.ra.hour, apparent.dec.degree)

class CatalogLoader:
    """Loads celestial objects from catalog CSV files."""
    
    def __init__(self):
        self.all = self.load_catalogs()
        self.all["solar_system"] = []
        self.all["by_constellation"] = []
        self.messier = self.all.get('messier', [])
        self.ngc = self.all.get('ngc', [])

    def get_catalogs(self):
        return list(self.all.keys())

    def load_catalog(self, file_path: str) -> List[CelestialObject]:
        """Load celestial objects from a CSV catalog file."""
        objects = []
        
        if not os.path.exists(file_path):
            print(f"Warning: Catalog file not found: {file_path}")
            return objects
        
        try:
            with open(file_path, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    objects.append(CelestialObject.from_csv_row(row))
                    
            print(f"Loaded {len(objects)} objects from {file_path}")
            return objects
        
        except Exception as e:
            print(f"Error loading catalog {file_path}: {e}")
            return []
    
    def load_catalogs(self, base_dir: str = None) -> Dict[str, List[CelestialObject]]:
        """Load all catalog files from the astronomy/catalog directory."""
        if base_dir is None:
            # Use the current file's directory to find the catalog folder
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog")
        
        catalogs = {}
        
        for file_name in os.listdir(base_dir):
            if file_name.endswith('.csv'):
                catalog_name = os.path.splitext(file_name)[0]
                file_path = os.path.join(base_dir, file_name)
                catalogs[catalog_name] = self.load_catalog(file_path)
                
        return catalogs
    
    def search_objects(self, **criteria) -> List[CelestialObject]:
        all_results = []
        
        # Search through all catalogs and collect matching objects
        for catalog_name, catalog_objects in self.all.items():
            catalog_results = catalog_objects.copy()
            
            # Filter by specified criteria
            if 'type' in criteria:
                catalog_results = [obj for obj in catalog_results if obj.type == criteria['type']]
                
            if 'name' in criteria:
                catalog_results = [obj for obj in catalog_results if obj.name == criteria['name']]
                
            if 'v_mag_max' in criteria:
                catalog_results = [obj for obj in catalog_results if obj.v_mag <= criteria['v_mag_max']]
                
            if 'v_mag_min' in criteria:
                catalog_results = [obj for obj in catalog_results if obj.v_mag >= criteria['v_mag_min']]
                
            if 'contains_comments' in criteria:
                catalog_results = [obj for obj in catalog_results if criteria['contains_comments'].lower() in obj.comments.lower()]
            
            # Add matching objects from this catalog to the overall results
            all_results.extend(catalog_results)
                
        return all_results