from astropy.io import ascii
from astropy.table import Table
import numpy as np
import time
import matplotlib
import matplotlib.pyplot as plt
import os
from utils import plt_to_img
import threading

def clean(n) -> str:
    if n is np.ma.masked:
        return ''
    n = str(n)
    n = n.strip()
    return n.lower()

class Stars:
    def __init__(self, ephemeris):
        self.ephemeris = ephemeris
        self.planet_cache = {}
        self.cache_time = None
        self.cache_duration = 5  # 5 seconds
        self._render_lock = threading.Lock()
        # Assume prebuilt Tycho catalog is available with names
        start = time.time()
        print("Loading Tycho catalog...", end=' ')
        dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.normpath(os.path.join(dir, 'tyc.fits'))
        self.tycho = Table.read(file)
        print(f"Done in {time.time() - start:.2f} seconds")

    def search_by_name(self, n: str):
        n = clean(n)
        name_col = self.tycho['Name'].filled('')
        name_strings = np.array([clean(n) for n in name_col])

        results = self.tycho[name_strings == n]
        return results

    def search_by_coordinate(self, ra: float, dec: float, radius: float = 0.05): # FOV in degrees
        ra = float(ra) #.item()
        dec = float(dec)
        radius = float(radius)

        # Convert radius from degrees to radians
        radius_rad = np.radians(radius)

        # Calculate the distance in degrees
        delta_ra = np.radians(self.tycho['RAdeg'] - ra)
        delta_dec = np.radians(self.tycho['DEdeg'] - dec)

        # Haversine formula to calculate distance
        a = (np.sin(delta_dec / 2) ** 2 +
            np.cos(np.radians(dec)) * np.cos(np.radians(self.tycho['DEdeg'])) *
            np.sin(delta_ra / 2) ** 2)
        distance_rad = 2 * np.arcsin(np.sqrt(a))

        # Filter results within the specified radius
        within_radius = distance_rad <= radius_rad
        star_results = self.tycho[within_radius]
        
        # Get planets in FOV
        planets_in_fov = self.get_planets_in_fov(ra, dec, radius)
        
        if planets_in_fov:
            combined_results = []
            
            for star in star_results:
                combined_results.append({
                    'Name': star['Name'],
                    'RAdeg': star['RAdeg'],
                    'DEdeg': star['DEdeg'],
                    'Vmag': star['Vmag'],
                    'is_planet': False
                })
            
            for planet in planets_in_fov:
                combined_results.append(planet)
            
            return combined_results
        else:
            return [{'Name': star['Name'], 'RAdeg': star['RAdeg'], 'DEdeg': star['DEdeg'], 
                    'Vmag': star['Vmag'], 'is_planet': False} for star in star_results]
    
    # will probably combine/add to telescope
    def radius_from_telescope(self, focal_length: float, eyepiece: float, eyepiece_afov: float):
        mag = focal_length / eyepiece
        fov = eyepiece_afov / mag
        return (fov / 2)

    def rotate(self, x, y, angle_deg):
        angle_rad = np.radians(angle_deg)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        x_rot = x * cos_a - y * sin_a
        y_rot = x * sin_a + y * cos_a
        return x_rot, y_rot

    def project_to_view(self, objects, center_ra, center_dec, radius_deg, rotation: float = 0):
        """Project both stars and planets to view coordinates"""
        ra0 = np.radians(center_ra)
        dec0 = np.radians(center_dec)

        results = []
        
        for obj in objects:
            ra = np.radians(obj['RAdeg'])
            dec = np.radians(obj['DEdeg'])
            
            delta_ra = (ra - ra0 + np.pi) % (2 * np.pi) - np.pi
            
            cos_c = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(delta_ra)
            cos_c = np.clip(cos_c, 1e-12, None)
            
            x = np.cos(dec) * np.sin(delta_ra) / cos_c
            y = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(delta_ra)) / cos_c
            
            x = -x
            x, y = self.rotate(x, y, rotation)
            
            radius_rad = np.radians(radius_deg)
            x_norm = x / radius_rad
            y_norm = y / radius_rad
            r_deg = np.degrees(np.sqrt(x**2 + y**2))
            
            results.append({
                'object': obj,
                'x': x_norm,
                'y': y_norm,
                'r': r_deg
            })

        return results

    def render_view(self, projected):
        with self._render_lock:
            fig, ax = plt.subplots()
            fig.set_facecolor('black')
            fig.set_dpi(50)
            ax.set_aspect('equal')
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)

            # Draw FOV circle
            circle = plt.Circle((0, 0), 1, color='red', fill=False)
            ax.add_patch(circle)

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
                    size = max(1, 15 - mag)
                    ax.plot(x, y, 'o', markersize=size, color='white')
                    
                    # Label bright stars
                    label_pos = (round(x + 0.03, 1), round(y, 1))
                    name = str(obj['Name']).strip().replace("--", "").upper()
                    if mag < 10 and label_pos not in labeled_positions and len(name) > 0:
                        ax.text(*label_pos, name, color='orange', fontsize=15, clip_on=True, fontweight='bold')
                        labeled_positions.add(label_pos)

            ax.set_facecolor('black')
            plt.axis('off')
            matplotlib.pyplot.close()
            return plt_to_img(fig)
        

    def get_planets_in_fov(self, ra, dec, radius):
        current_time = time.time()
        
        # Check if we need to refresh planet cache
        if (self.cache_time is None or 
            current_time - self.cache_time > self.cache_duration or
            not self.planet_cache):
            
            if self.ephemeris:
                self.planet_cache = self.ephemeris.get_current_positions()
                self.cache_time = current_time
            else:
                self.planet_cache = {}
        
        # Filter planets within FOV
        planets_in_fov = []
        
        for planet_name, planet_data in self.planet_cache.items():
            if self.is_within_radius(ra, dec, planet_data['RAdeg'], planet_data['DEdeg'], radius):
                planets_in_fov.append(planet_data)
        
        return planets_in_fov
    
    def is_within_radius(self, center_ra, center_dec, target_ra, target_dec, radius): # distance with haversine formula
        radius_rad = np.radians(radius)
        delta_ra = np.radians(target_ra - center_ra)
        delta_dec = np.radians(target_dec - center_dec)
        
        a = (np.sin(delta_dec / 2) ** 2 +
             np.cos(np.radians(center_dec)) * np.cos(np.radians(target_dec)) *
             np.sin(delta_ra / 2) ** 2)
        distance_rad = 2 * np.arcsin(np.sqrt(a))
        
        return distance_rad <= radius_rad