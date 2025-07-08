""" Custom Starfield Renderer. Use with scope, target manager, stars, and ephem """
from astropy.coordinates import SkyCoord

from PIL import Image, ImageDraw
import numpy as np

class NavigationStarfield:
    def __init__(self, scope):
        self.scope = scope
        self.tm = scope.target_manager
        self.stars = self.tm.stars

    def render(self):
        stars, name = self.render_stars()
        nav = self.simple_nav(stars)
        return nav, name

    def render_stars(self):
        r = self.stars.radius_from_telescope(self.scope.focal_length, self.scope.eyepiece, self.scope.eyepiece_fov) * 1
        ra, dec = self.scope.get_position()
        nearby = self.stars.search_by_coordinate(ra=ra, dec=dec, radius=r)
        
        brightest = None
        for star in nearby:
            if brightest is None or star['Vmag'] < brightest['Vmag']:
                brightest = star
        projected = self.stars.project_to_view(nearby, center_ra=ra, center_dec=dec, radius_deg=r, rotation=self.scope.viewing_angle)
        return self.stars.render_view(projected), str(brightest['Name']) if brightest else "--"
                        
    def simple_nav(self, image: Image, field_size: float = 0.8333):
        current_ra, current_dec = self.scope.get_position()
        if current_ra is None:
            return None
        target_ra, target_dec = self.scope.target_manager.get_target_position()
        if target_ra is None or target_dec is None:
            return None
        
        image_size = 240
        draw = ImageDraw.Draw(image)
        if image is None:
            image = Image.new("RGB", (image_size, image_size), "black")

        # Convert RA/Dec to SkyCoord objects
        current_coord = SkyCoord(ra=current_ra, dec=current_dec, unit='deg', frame='gcrs')
        target_coord = SkyCoord(ra=target_ra, dec=target_dec, unit='deg', frame='gcrs')
        
        #print(f"XOFFSET:{current_ra-target_ra}")
        #print(f"YOFFSET:{current_dec-target_dec}")

        #print(f"Current RA: {current_ra}, Dec: {current_dec}")
        #print(f"Target RA: {target_ra}, Dec: {target_dec}")
        # Calculate angular distance and position angle
        distance = current_coord.separation(target_coord).deg
        angle = current_coord.position_angle(target_coord).deg  # angle from current to target, counterclockwise from N
        print(f"Distance: {distance}")
        center_x, center_y = image_size // 2, image_size // 2

        if distance <= field_size/2:
            # Target in field of view, somewhere on screen
            radius = 80
            draw.ellipse(
                (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                outline="green", width=3
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
                fill="green"
            )


        return image
