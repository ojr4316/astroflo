import numpy as np
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from utils import plt_to_img
from threading import Lock
from PIL import Image, ImageDraw
from observation_context import TelescopeState, TelescopeOptics, TargetState
from astronomy.catalog import Catalog

def rotate(x, y, angle_deg):
        angle_rad = np.radians(angle_deg)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        x_rot = x * cos_a - y * sin_a
        y_rot = x * sin_a + y * cos_a
        return x_rot, y_rot

def project_to_view(objects, center_ra, center_dec, radius_deg, rotation=0):
        ra0 = np.radians(center_ra)
        dec0 = np.radians(center_dec)
        
        results = []
        for obj in objects:
            ra = np.radians(obj['RAdeg'])
            dec = np.radians(obj['DEdeg'])

            delta_ra = ra - ra0
            
            # Gnomonic projection
            cos_c = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(delta_ra)
            if cos_c <= 0:
                continue
                
            angular_distance = np.degrees(np.arccos(np.clip(cos_c, 0, 1)))
            if angular_distance > radius_deg:
                continue
        
            x = -np.cos(dec) * np.sin(delta_ra) / cos_c 
            y = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(delta_ra)) / cos_c
            
            x, y = rotate(x, y, rotation)

            radius_rad = np.radians(radius_deg)
            x_norm = x / radius_rad
            y_norm = y / radius_rad
            
            if x_norm**2 + y_norm**2 > 1:
                continue
            
            results.append({
                'object': obj,
                'x': x_norm,
                'y': y_norm,
                'r': angular_distance
            })
        
        return results

class StarfieldRenderer:
    def __init__(self, catalog: Catalog, telescope_state: TelescopeState, telescope_optics: TelescopeOptics, target_state: TargetState):
        self.catalog = catalog
        self.telescope_state = telescope_state
        self.telescope_optics = telescope_optics
        self.target_state = target_state
        self._render_lock = Lock()
    
    def render_view(self, projected, zoom=1):
        with self._render_lock:
            fig, ax = plt.subplots()
            fig.set_facecolor('black')
            fig.set_dpi(50)
            ax.set_aspect('equal')
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)
            circle = plt.Circle((0, 0), 1, color='red', fill=False)
            ax.add_patch(circle)
            ax.text(-0.98, 0, 'E', color='white', fontsize=12, va='center', ha='right')
            ax.text(1.02, 0, 'W', color='white', fontsize=12, va='center', ha='right')

            # Plot objects
            labeled_positions = set()
            for item in projected:
                obj = item['object']
                x, y = item['x'], item['y']
                mag = obj['Vmag']
                is_planet = obj.get('is_planet', False)
                
                if is_planet:
                    # Render planets differently
                    size = max(8, 20 - mag)  # Planets are generally larger
                    color = 'yellow' if obj['Name'] == 'SUN' else 'cyan'
                    marker = 'o' if obj['Name'] != 'SUN' else '*'
                    ax.plot(x, y, marker, markersize=size, color=color, markeredgecolor='white', markeredgewidth=2)
                    
                    label_pos = (round(x + 0.03, 1), round(y, 1))
                    if label_pos not in labeled_positions:
                        ax.text(*label_pos, obj['Name'], color='red', fontsize=12, clip_on=True, fontweight='bold')
                        labeled_positions.add(label_pos)
                else:
                    # Render stars normally
                    size = min(max(1, 25 - mag*2), 15)/(1 if zoom == 1 else (zoom*2 if zoom < 1 else zoom/2))
                    ax.plot(x, y, 'o', markersize=size, color='white')
                    
                    # Label bright stars
                    label_pos = (round(x + 0.03, 1), round(y, 1))
                    name = str(obj['Name']).strip().replace("--", "").upper()
                    if mag < 6 and label_pos not in labeled_positions and len(name) > 0:
                        ax.text(*label_pos, name, color='orange', fontsize=15, clip_on=True, fontweight='bold')
                        labeled_positions.add(label_pos)

            ax.set_facecolor('black')
            plt.axis('off')
            matplotlib.pyplot.close()
            return plt_to_img(fig)
    
    def add_navigation_overlay(self, image: Image):
        current_ra, current_dec = self.telescope_state.position
        if current_ra is None:
            return None, 0

        if not self.target_state.has_target():
            return None, 0

        target_ra = self.target_state.ra
        target_dec = self.target_state.dec

        image_size = 240
        overlay = Image.new("RGBA", (image_size, image_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        r = self.telescope_optics.field_radius() * self.telescope_optics.zoom
        x_norm, y_norm, r_deg = self.project_target_to_view(
            target_ra, target_dec, current_ra, current_dec, r, self.telescope_state.roll
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
    
    def render(self):
        r = self.telescope_optics.field_radius()
        ra, dec = self.telescope_state.position
        nearby = self.catalog.search_by_coordinate(ra=ra, dec=dec, radius=r, mag_limit=self.telescope_optics.get_limiting_magnitude())

        projected = project_to_view(nearby, center_ra=ra, center_dec=dec, radius_deg=r, rotation=self.telescope_state.roll)
        stars =  self.render_view(projected, self.telescope_optics.zoom)

        dist = 0
        if self.target_state.has_target():
            stars, dist = self.add_navigation_overlay(stars)
        return stars, dist


                  