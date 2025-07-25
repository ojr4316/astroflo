""" Custom Starfield Renderer. Use with scope, target manager, stars, and ephem """
from PIL import Image, ImageDraw
import numpy as np

class NavigationStarfield:
    def __init__(self, scope):
        self.scope = scope
        self.tm = scope.target_manager
        self.stars = self.tm.stars

    def render(self):
        # Returns annotated starfield image and targeting information
        stars, brightest = self.render_stars()
        dist = 0
        if self.tm.has_target():
            stars, dist = self.simple_nav(stars)
        return stars, dist

    def render_stars(self):
        r = self.stars.radius_from_telescope(self.scope.focal_length, self.scope.eyepiece, self.scope.eyepiece_fov) * self.scope.zoom
        ra, dec = self.scope.get_position()
        nearby = self.stars.search_by_coordinate(ra=ra, dec=dec, radius=r, mag_limit=self.scope.get_limiting_magnitude())
        
        brightest = None
        for star in nearby:
            if brightest is None or star['Vmag'] < brightest['Vmag']:
                brightest = star
        projected = self.stars.project_to_view(nearby, center_ra=ra, center_dec=dec, radius_deg=r, rotation=self.scope.viewing_angle)
        return self.stars.render_view(projected, self.scope.zoom), str(brightest['Name']) if brightest else "--"
                        
    def project_target_to_view(self, target_ra, target_dec, center_ra, center_dec, radius_deg, rotation=0):
        ra0 = np.radians(center_ra)
        dec0 = np.radians(center_dec)
        
        ra = np.radians(target_ra)
        dec = np.radians(target_dec)
        
        delta_ra = (ra - ra0 + np.pi) % (2 * np.pi) - np.pi
        
        # Compute cos_c denominator
        cos_c = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(delta_ra)
        
        # Avoid division by zero
        cos_c = np.clip(cos_c, 1e-12, None)
        x = np.cos(dec) * np.sin(delta_ra) / cos_c
        y = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(delta_ra)) / cos_c
        
        x = -x
        x, y = self.stars.rotate(x, y, rotation)
        
        # Calculate angular separation directly from the spherical trig formula
        # This gives the great-circle distance in radians
        angular_distance_rad = np.arccos(np.clip(cos_c, -1.0, 1.0))
        
        # Convert to degrees
        r_deg = np.degrees(angular_distance_rad)
        
        # Calculate x_norm and y_norm for UI display purposes
        radius_rad = np.radians(radius_deg)
        if radius_rad > 0:
            x_norm = x / radius_rad
            y_norm = y / radius_rad
        else:
            x_norm, y_norm = 0, 0
        
        return x_norm, y_norm, r_deg

    def simple_nav(self, image: Image):
        current_ra, current_dec = self.scope.get_position()
        if current_ra is None:
            return None, 0
        
        if self.scope.target_manager.ra is None:
            return None, 0
            
        target_ra = self.scope.target_manager.ra
        target_dec = self.scope.target_manager.dec
        
        image_size = 240
        overlay = Image.new("RGBA", (image_size, image_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        r = self.stars.radius_from_telescope(self.scope.focal_length, self.scope.eyepiece, self.scope.eyepiece_fov) * self.scope.zoom
        x_norm, y_norm, r_deg = self.project_target_to_view(
            target_ra, target_dec, current_ra, current_dec, r, self.scope.viewing_angle
        )
        
        center_x, center_y = image_size // 2, image_size // 2

        if r_deg <= r:
            # Target in field of view - use projected coordinates
            # Convert from normalized coordinates (-1 to 1) to pixel coordinates
            # Note: y-axis is flipped in image coordinates (top-left origin)
            pixel_x = center_x + x_norm * (image_size // 2)
            pixel_y = center_y - y_norm * (image_size // 2)  # Flip y-axis
            
            draw.ellipse(
                (pixel_x - 8, pixel_y - 8, pixel_x + 8, pixel_y + 8),
                outline="green", width=3
            )
            draw.line((pixel_x - 15, pixel_y, pixel_x + 15, pixel_y), fill="green", width=2)
            draw.line((pixel_x, pixel_y - 15, pixel_x, pixel_y + 15), fill="green", width=2)
        else:
            # Target is outside FOV - draw directional arrow using projected coordinates
            direction_len = np.sqrt(x_norm**2 + y_norm**2)
            if direction_len > 0:
                x_dir = x_norm / direction_len
                y_dir = y_norm / direction_len
                
                max_arrow_len = image_size // 2 - 10
                end_x = center_x + x_dir * max_arrow_len
                end_y = center_y - y_dir * max_arrow_len

                color = (255, 0, 0, 100)
                draw.line((center_x, center_y, end_x, end_y), fill=color, width=3)
                draw.ellipse(
                    (end_x - 5, end_y - 5, end_x + 5, end_y + 5),
                    fill=color
                )

        image.convert("RGBA")
        image.alpha_composite(overlay)
        image.convert("RGB")
        return image, r_deg
