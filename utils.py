import os
import io
import numpy as np
from PIL import Image
def is_pi():
    return os.name != 'nt' and os.uname().nodename == "rpi"

def plt_to_img(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    img = Image.open(buf)
    return img.resize((240, 240))

def radec_to_vector(ra_deg:float, dec_deg:float):
    ra = np.radians(ra_deg)
    dec = np.radians(dec_deg)

    x = np.cos(dec) * np.cos(ra)
    y = np.cos(dec) * np.sin(ra)
    z = np.sin(dec)

    return np.array([x, y, z])

def solve_rotation(camera, telescope):
    assert camera.shape == telescope.shape

    H = camera @ telescope.T
    U, _, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T

    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T
    return R

def apply_rotation(R, ra, dec):
    vec = radec_to_vector(ra, dec)
    telescope = R @ vec

    x, y, z = telescope
    dec = np.degrees(np.arcsin(z))
    ra = np.degrees(np.arctan2(y, x)) % 360

    return ra, dec

def haversine_dist(current_ra, current_dec, target_ra, target_dec, roll=0):
    current_ra_rad = np.radians(current_ra)
    current_dec_rad = np.radians(current_dec)
    target_ra_rad = np.radians(target_ra)
    target_dec_rad = np.radians(target_dec)

    delta_ra = target_ra_rad - current_ra_rad
    delta_dec = target_dec_rad - current_dec_rad

    a = (np.sin(delta_dec / 2) ** 2 +
         np.cos(current_dec_rad) * np.cos(target_dec_rad) * (np.sin(delta_ra / 2) ** 2))
    c = 2 * np.arcsin(np.sqrt(a))

    roll_adjustment = np.radians(roll)
    c += roll_adjustment

    return c
   