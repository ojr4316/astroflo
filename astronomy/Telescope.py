from astropy.coordinates import AltAz, EarthLocation, SkyCoord, Angle
import astropy.units as u

rochesterLat = 43.1566
rochesterLong = -77.6088
rochesterElevation = 150

rochester = EarthLocation(
    lat=rochesterLat*u.deg, lon=rochesterLong*u.deg, height=rochesterElevation*u.m)

class Telescope:
    def __init__(self, aperature: int, focal_length: int, eyepiece: int, eyepiece_fov: int, zoom: int = 1):
        self.aperture = aperature
        self.focal_length = focal_length
        self.eyepiece = eyepiece
        self.eyepiece_fov = eyepiece_fov
        self.zoom = zoom # barlow

        self.position = None
        self.last_position = None
        self.camera_offset = (0, 0)

        self.location = rochester

        self.speed = 0
       
    def set_camera_offset(self, x: float, y: float):
        self.camera_offset = (x, y)

    def get_position(self):
        if self.position is None:
            return None
        return self.position + self.camera_offset
        
    def set_position(self, ra: float, dec: float):
        if self.last_position is not None:
            self.speed = ((ra - self.last_position[0]) ** 2 + (dec - self.last_position[1]) ** 2) ** 0.5
        if self.position is not None:
            self.last_position = self.position
        self.position = (ra, dec)

    def get_magnification(self):
        return self.focal_length / self.eyepiece
    
    def get_limiting_magnitude(self):
        aperture_inches = self.aperture / (7 * 25.4)
        limiting_magnitude = 7.5 + 5 * (aperture_inches / 4) ** 0.5
        return limiting_magnitude
    
