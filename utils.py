import os
import io
import numpy as np
from typing import Tuple
from PIL import Image
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from astropy.time import Time
import astropy.units as u

def is_pi() -> bool:
    return os.name != 'nt' and os.uname().nodename == "rpi"

def plt_to_img(fig) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    img = Image.open(buf)
    return img.resize((240, 240))

def rotation_between_vectors(v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    v1 = v1 / np.linalg.norm(v1)
    v2 = v2 / np.linalg.norm(v2)

    dot_product = np.clip(np.dot(v1, v2), -1.0, 1.0)
    
    # Anti-parallel case
    if dot_product < -0.99999:
        # Find any perpendicular vector
        perp = np.array([1, 0, 0]) if abs(v1[0]) < 0.9 else np.array([0, 1, 0])
        axis = np.cross(v1, perp)
        axis = axis / np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)  # 180° rotation
    
    axis = np.cross(v1, v2)
    angle = np.arccos(dot_product)

    if np.linalg.norm(axis) < 1e-8:
        return np.eye(3)  # vectors are already aligned

    axis = axis / np.linalg.norm(axis)
    k = np.array([
        [0, -axis[2], axis[1]],
        [axis[2], 0, -axis[0]],
        [-axis[1], axis[0], 0]
    ])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k

def rotate_about_vector(v: np.ndarray, angle_deg: float):
    angle = np.radians(angle_deg)
    v = v / np.linalg.norm(v)
    k = np.array([
        [0, -v[2], v[1]],
        [v[2], 0, -v[0]],
        [-v[1], v[0], 0]
    ])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k

def radec_to_vector(ra_deg:float, dec_deg:float):
    ra = np.radians(ra_deg)
    dec = np.radians(dec_deg)

    x = np.cos(dec) * np.cos(ra)
    y = np.cos(dec) * np.sin(ra)
    z = np.sin(dec)

    return np.array([x, y, z])

def solve_rotation(camera: Tuple[float, float], telescope: Tuple[float, float], camera_roll: float) -> np.ndarray:
    cam_vec = radec_to_vector(camera[0], camera[1])
    tel_vec = radec_to_vector(telescope[0], telescope[1])

    align = rotation_between_vectors(cam_vec, tel_vec)
    roll = rotate_about_vector(tel_vec, camera_roll)

    return align @ roll

def apply_rotation(rotation: np.ndarray, ra: float, dec: float, roll: float) -> Tuple[float, float]:
    vec = radec_to_vector(ra, dec)
    telescope = rotation @ vec
    roll_correct = rotate_about_vector(telescope, roll)
    telescope = roll_correct @ telescope

    x, y, z = telescope
    dec = np.degrees(np.arcsin(np.clip(z, -1.0, 1.0)))
    ra = np.degrees(np.arctan2(y, x)) % 360

    return ra, dec

def haversine_dist(current_ra: float, current_dec: float, target_ra: float, target_dec: float) -> float:
    current_ra_rad = np.radians(current_ra)
    current_dec_rad = np.radians(current_dec)
    target_ra_rad = np.radians(target_ra)
    target_dec_rad = np.radians(target_dec)

    delta_ra = target_ra_rad - current_ra_rad
    delta_ra = np.arctan2(np.sin(delta_ra), np.cos(delta_ra))
    delta_dec = target_dec_rad - current_dec_rad

    a = (np.sin(delta_dec / 2) ** 2 +
         np.cos(current_dec_rad) * np.cos(target_dec_rad) * (np.sin(delta_ra / 2) ** 2))
    c = 2 * np.arcsin(np.sqrt(a))

    return c

def distance_north_east(current_ra: float, current_dec: float, target_ra: float, target_dec: float, roll: float = 0) -> Tuple[float, float]:
    current_ra_rad = np.radians(current_ra)
    current_dec_rad = np.radians(current_dec)
    target_ra_rad = np.radians(target_ra)
    target_dec_rad = np.radians(target_dec)
    
    delta_ra = target_ra_rad - current_ra_rad
    delta_ra = np.arctan2(np.sin(delta_ra), np.cos(delta_ra))
    
    north_raw = target_dec_rad - current_dec_rad
    east_raw = delta_ra * np.cos(current_dec_rad)  # Account for meridian convergence
    
    roll_rad = np.radians(-roll)
    cos_roll = np.cos(roll_rad)
    sin_roll = np.sin(roll_rad)
    
    north_rotated = cos_roll * north_raw - sin_roll * east_raw
    east_rotated = sin_roll * north_raw + cos_roll * east_raw
    
    return north_rotated, east_rotated

def distance_descriptor(dist: float):
        dist = abs(dist)
        if dist < 1:
            return "nearby"
        elif dist < 20:
            return "close"
        elif dist < 80:
            return "far"
        else:
            return "distant"

def radec_to_altaz(ra: float, dec: float, time: Time, location: EarthLocation) -> Tuple[float, float]:
    coord = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs')
    altaz_frame = AltAz(obstime=time, location=location)
    altaz_coord = coord.transform_to(altaz_frame)
    
    return altaz_coord.alt.deg, altaz_coord.az.deg

def altaz_to_radec(alt: float, az: float, time: Time, location: EarthLocation) -> Tuple[float, float]:
    altaz_frame = AltAz(obstime=time, location=location)
    coord = SkyCoord(alt=alt*u.deg, az=az*u.deg, frame=altaz_frame)
    icrs_coord = coord.transform_to('icrs')
    
    return icrs_coord.ra.deg, icrs_coord.dec.deg