import csv
import os
from typing import List, Optional, Dict
from pathlib import Path
from astropy.coordinates import SkyCoord, EarthLocation, GCRS
from astropy.time import Time
import astropy.units as u

rochesterLat = 43.1566
rochesterLong = -77.6088
rochesterElevation = 150
rochester = EarthLocation(lat=rochesterLat*u.deg, lon=rochesterLong*u.deg, height=rochesterElevation*u.m)

def get_apparent_radec(ra_hours: float, dec_deg: float, location: EarthLocation,
                       time_utc: str = None):
    ra_deg = ra_hours * 15

    j2000 = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')
    time = Time(time_utc) if time_utc else Time.now()

    obsgeoloc, obsgeovel = location.get_gcrs_posvel(time)
    gcrs = j2000.transform_to(GCRS(obstime=time, obsgeoloc=obsgeoloc, obsgeovel=obsgeovel))
    apparent = SkyCoord(ra=gcrs.ra, dec=gcrs.dec, frame='icrs')

    return (apparent.ra.hour, apparent.dec.degree)

class CelestialObject:
    """Represents a celestial object from the catalog."""
    
    def __init__(self, 
                 messier_id: Optional[int] = None,
                 ngc_id: str = "",
                 v_mag: float = 0.0,
                 obj_type: str = "",
                 comments: str = "",
                 ra: float = 0.0,
                 dec: float = 0.0,
                 ref: str = "",
                 is_up: bool = False):
        self.messier_id = messier_id
        self.ngc_id = ngc_id
        self.v_mag = v_mag
        self.type = obj_type
        self.comments = comments
        self.ra = ra
        self.dec = dec
        self.ref = ref
        self.is_up = is_up
    
    def __str__(self) -> str:
        messier_str = f"M{self.messier_id}" if self.messier_id else ""
        ngc_str = f"{self.ngc_id}" if self.ngc_id else ""
        
        if messier_str and ngc_str:
            id_str = f"{messier_str} ({ngc_str})"
        else:
            id_str = messier_str or ngc_str
            
        return f"{id_str}: {self.type}, Mag: {self.v_mag}, RA: {self.ra}, Dec: {self.dec}"
    
    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'CelestialObject':
        """Create a CelestialObject from a CSV row dictionary."""
        messier_id = int(row['messier_id']) if row['messier_id'] else None
        
        v_mag = float(row['v_mag']) if row['v_mag'] else 0.0
        ra = float(row['ra']) if row['ra'] else 0.0
        dec = float(row['dec']) if row['dec'] else 0.0
        is_up = bool(row['is_up']) if row['is_up'] else False
        
        return cls(
            messier_id=messier_id,
            ngc_id=row['ngc_id'],
            v_mag=v_mag,
            obj_type=row['type'],
            comments=row['comments'],
            ra=ra,
            dec=dec,
            ref=row['ref'],
            is_up=is_up
        )


class CatalogLoader:
    """Loads celestial objects from catalog CSV files."""
    
    def __init__(self):
        self.all = self.load_catalogs()
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
        """
        Search for celestial objects matching specific criteria.
        
        Args:
            **criteria: Keyword arguments for filtering (e.g., type='OC', v_mag_max=5.0)
                Supported criteria:
                - type: Object type (exact match)
                - messier_id: Messier ID (exact match)
                - ngc_id: NGC ID (exact match)
                - v_mag_max: Maximum visual magnitude (objects brighter than this)
                - v_mag_min: Minimum visual magnitude
                - contains_comments: Substring to search for in comments
        
        Returns:
            List of matching objects
        """
        all_results = []
        
        # Search through all catalogs and collect matching objects
        for catalog_name, catalog_objects in self.all.items():
            catalog_results = catalog_objects.copy()
            
            # Filter by specified criteria
            if 'type' in criteria:
                catalog_results = [obj for obj in catalog_results if obj.type == criteria['type']]
                
            if 'messier_id' in criteria:
                catalog_results = [obj for obj in catalog_results if obj.messier_id == criteria['messier_id']]
                
            if 'ngc_id' in criteria:
                catalog_results = [obj for obj in catalog_results if obj.ngc_id == criteria['ngc_id']]
                
            if 'v_mag_max' in criteria:
                catalog_results = [obj for obj in catalog_results if obj.v_mag <= criteria['v_mag_max']]
                
            if 'v_mag_min' in criteria:
                catalog_results = [obj for obj in catalog_results if obj.v_mag >= criteria['v_mag_min']]
                
            if 'contains_comments' in criteria:
                catalog_results = [obj for obj in catalog_results if criteria['contains_comments'].lower() in obj.comments.lower()]
            
            # Add matching objects from this catalog to the overall results
            all_results.extend(catalog_results)
                
        return all_results
    

# Example usage:
if __name__ == "__main__":
    catalogs = CatalogLoader()   

    # Search for Messier 5
    m5_results = catalogs.search_objects(messier_id=5)
    if m5_results:
        m5 = m5_results[0]  # Get the first (and likely only) result
        print(m5)
        print(f"RA: {m5.ra}, Dec: {m5.dec}")
        ra, dec = get_apparent_radec(m5.ra, m5.dec, rochester)
        print(f"Apparent RA: {ra:.4f} hours, Apparent Dec: {dec:.4f} degrees")
    else:
        print("Messier 5 not found in the catalog.")
   