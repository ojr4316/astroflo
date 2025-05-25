import os

def is_pi():
    return os.name != 'nt' and os.uname().nodename == "rpi"