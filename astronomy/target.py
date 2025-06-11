from astronomy.catalog import CatalogLoader, CelestialObject, get_apparent_radec
from astropy.coordinates import SkyCoord, EarthLocation, GCRS

from PIL import Image, ImageDraw
import numpy as np

class TargetManager:

    def __init__(self, location: EarthLocation):
        self.location = location
        self.catalog_loader = CatalogLoader()

        self.target = None

        self.catalog = None
        self.index = 0 
        
        self.distance = 0.0

    
    def set_target(self, target: CelestialObject):
        self.target = target
        
    def get_target_position(self):
        if self.target is None:
            return None
        return (self.target.ra, self.target.dec) #get_apparent_radec(self.target.ra, self.target.dec, self.location)
    
    def get_catalog(self):
        return [t.name for t in self.catalog_loader.all[self.catalog]]
    

    def simple_nav(self, current_ra: float, current_dec: float, field_size: float = 0.8333):
        if self.target is None:
            return None

        target_ra, target_dec = self.get_target_position()
        if target_ra is None or target_dec is None:
            return None

        image_size = 240
        image = Image.new("RGB", (image_size, image_size), "black")
        draw = ImageDraw.Draw(image)

        # Convert RA/Dec to SkyCoord objects
        current_coord = SkyCoord(ra=current_ra, dec=current_dec, unit='deg', frame='gcrs')
        target_coord = SkyCoord(ra=target_ra, dec=target_dec, unit='deg', frame='gcrs')
        print(f"Current RA: {current_ra}, Dec: {current_dec}")
        print(f"Target RA: {target_ra}, Dec: {target_dec}")
        # Calculate angular distance and position angle
        distance = current_coord.separation(target_coord).deg
        angle = current_coord.position_angle(target_coord).deg  # angle from current to target, counterclockwise from N
        print(f"Distance: {distance}, Field size: {field_size}")
        center_x, center_y = image_size // 2, image_size // 2

        if distance <= field_size/2:
            # Target in field of view, somewhere on screen
            radius = 80
            draw.ellipse(
                (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                outline="red", width=3
            )

            # TODO: estimate where it is in FOV
        else:
            # Target is outside FOV — draw a capped-length arrow
            max_arrow_len = image_size // 2 - 10
            arrow_length = max_arrow_len

            rad_angle = np.radians(angle)
            end_x = center_x + arrow_length * np.sin(rad_angle)
            end_y = center_y - arrow_length * np.cos(rad_angle)

            draw.line((center_x, center_y, end_x, end_y), fill="red", width=3)
            draw.ellipse(
                (end_x - 5, end_y - 5, end_x + 5, end_y + 5),
                fill="red"
            )


        return image
