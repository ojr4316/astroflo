import os
from PIL import Image
import io

def is_pi():
    return os.name != 'nt' and os.uname().nodename == "rpi"

def plt_to_img(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    img = Image.open(buf)
    return img.resize((240, 240))
