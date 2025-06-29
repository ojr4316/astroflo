from astropy.io import ascii
from astropy.table import Table
import numpy as np
import time
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
    def __init__(self):
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

        results = self.tycho[within_radius]
        #matching_distances = distance_rad[within_radius]

        return results
    
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

    def project_to_view(self, stars, center_ra, center_dec, radius_deg, rotation: float = 0):
        ra0 = np.radians(center_ra)
        dec0 = np.radians(center_dec)

        ra = np.radians(stars['RAdeg'])
        dec = np.radians(stars['DEdeg'])

        delta_ra = (ra - ra0 + np.pi) % (2 * np.pi) - np.pi

        # Compute cos_c denominator
        cos_c = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(delta_ra)

        # Avoid division by zero
        cos_c = np.clip(cos_c, 1e-12, None)
        x = np.cos(dec) * np.sin(delta_ra) / cos_c
        y = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(delta_ra)) / cos_c

        x = -x
        x, y = self.rotate(x, y, rotation)  
        
        # Convert angular FOV radius to radians and normalize
        radius_rad = np.radians(radius_deg)
        x_norm = x / radius_rad
        y_norm = y / radius_rad
        r_deg = np.degrees(np.sqrt(x**2 + y**2))

        results = []
        for i in range(len(stars)):
            results.append({
                'star': stars[i],
                'x': x_norm[i],
                'y': y_norm[i],
                'r': r_deg[i]
            })

        return results

    _render_lock = threading.Lock()

    def render_view(self, projected):
        with self._render_lock:
            fig, ax = plt.subplots()
            fig.set_facecolor('black')
            fig.set_dpi(100) # 184
            ax.set_aspect('equal')
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)

            # Draw FOV circle
            circle = plt.Circle((0, 0), 1, color='red', fill=False)
            ax.add_patch(circle)

            # Plot stars
            for obj in projected:
                star = obj['star']
                x, y = obj['x'], obj['y']
                mag = star['Vmag']
                size = max(1, 15 - mag)  # Bright stars are bigger
                ax.plot(x, y, 'o', markersize=size, color='white')

                if mag < 6:
                    ax.text(x + 0.03, y, star['Name'], color='red', fontsize=8)

            ax.set_facecolor('black')
            plt.axis('off')
            #plt.close()
            return plt_to_img(fig)



#stars = Stars()
#r = stars.radius_from_telescope(1200, 25, 40)
#print(f"Telescope FOV is {r:.2f}")
#star = stars.search_by_name('polaris')

#s = time.time()
#nearby = stars.search_by_coordinate(ra=star['RAdeg'], dec=star['DEdeg'], radius=r)
#print(f"Found {len(nearby)} stars near {star['Name'][0]} at RA: {star['RAdeg'][0]}, DEC: {star['DEdeg'][0]}")
#projected = stars.project_to_view(nearby, center_ra=star['RAdeg'][0], center_dec=star['DEdeg'][0], radius_deg=r, rotation=180)
#stars.render_view(projected)
#print(f"Done in {time.time() - s:.2f} seconds")