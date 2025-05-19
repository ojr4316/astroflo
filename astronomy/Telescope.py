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

        self.load_settings()
       
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
    
    def modify(self, idx, increase=False):
        match(idx):
            case 0: self.aperture += (1 if increase else -1)
            case 1: self.focal_length += (1 if increase else -1)
            case 2: self.eyepiece += (1 if increase else -1)
            case 3: self.eyepiece_fov += (1 if increase else -1)
        self.save_settings()

    def get_settings(self):
        return {"aperture": self.aperture, "focal_length": self.focal_length, "eyepiece": self.eyepiece, "eyepiece_fov": self.eyepiece_fov}
    
    def get_cam_settings(self):
        return {"x_offset": f"{self.camera_offset[0]:.1f}", "y_offset": f"{self.camera_offset[1]:.1f}"}
    
    def save_settings(self):
        settings = self.get_settings().update(self.get_cam_settings())
        with open("settings.txt", "w") as f:
            for key, value in settings.items():
                f.write(f"{key}: {value}\n")
        print("Settings saved to settings.txt")

    def load_settings(self):
        settings = {}
        with open("settings.txt", "r") as f:
            for line in f:
                key, value = line.strip().split(": ")
                settings[key] = value
        self.aperture = int(settings["aperture"])
        self.focal_length = int(settings["focal_length"])
        self.eyepiece = int(settings["eyepiece"])
        self.eyepiece_fov = int(settings["eyepiece_fov"])
        self.camera_offset = (float(settings["x_offset"]), float(settings["y_offset"]))
        print("Settings loaded from settings.txt")