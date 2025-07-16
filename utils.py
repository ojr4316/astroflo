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