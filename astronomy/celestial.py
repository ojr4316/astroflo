from typing import Optional, Dict

""" Represents any sky target (Star, Galaxy, Planet, Moon, Asteroid, etc.)"""
class CelestialObject:     
    def __init__(self, 
                 name: str = "",
                 v_mag: float = 0.0,
                 obj_type: str = "",
                 comments: str = "",
                 ra: float = 0.0,
                 dec: float = 0.0,
                 ref: str = "",
                 is_up: bool = False):
        self.name = name
        self.v_mag = v_mag
        self.type = obj_type
        self.comments = comments
        self.ra = ra
        self.dec = dec
        self.ref = ref
        self.is_up = is_up
    
    def __str__(self) -> str:
        return f"{self.name}: {self.type}, Mag: {self.v_mag}, RA: {self.ra}, Dec: {self.dec}"
    
    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'CelestialObject':
        """Create a CelestialObject from a CSV row dictionary."""
        messier_id = int(row['messier_id']) if row['messier_id'] else None
        
        v_mag = float(row['v_mag']) if row['v_mag'] else 0.0
        ra = float(row['ra']) if row['ra'] else 0.0
        dec = float(row['dec']) if row['dec'] else 0.0
        is_up = False
        
        if messier_id is None:
            name = row['ngc_id']
        else:
            name = f"M{messier_id}"

        return cls(
            name=name,
            v_mag=v_mag,
            obj_type=row['type'],
            comments=row['comments'],
            ra=ra,
            dec=dec,
            ref=row['ref'],
            is_up=is_up
        )

