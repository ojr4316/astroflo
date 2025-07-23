import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "..", "settings.txt")
COORD_LOG = os.path.join(BASE_DIR, "..", "coord_log.txt")

class TelescopeSettings:
    def __init__(self, scope):
        self.scope = scope
        self.load()
        
    def get_settings(self):
        return {"aperture": self.scope.aperture, "focal_length": self.scope.focal_length, "eyepiece": self.scope.eyepiece, "eyepiece_fov": self.scope.eyepiece_fov}

    def get_cam_settings(self): # Camera Settings Page
        return {"x_offset": f"{self.scope.camera_offset[0]:.1f}", "y_offset": f"{self.scope.camera_offset[1]:.1f}", "view_angle": f"{self.scope.viewing_angle}"}
    
    def save(self): 
        settings = {**self.get_settings(), **self.get_cam_settings()}
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            for key, value in settings.items():
                f.write(f"{key}: {value}\n")

    def load(self):
        if not os.path.exists(SETTINGS_FILE):
            self.save()
            return
        settings = {}
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                key, value = line.strip().split(": ")
                settings[key] = value
        self.scope.aperture = int(settings["aperture"])
        self.scope.focal_length = int(settings["focal_length"])
        self.scope.eyepiece = int(settings["eyepiece"])
        self.scope.eyepiece_fov = int(settings["eyepiece_fov"])
        self.scope.camera_offset = (float(settings["x_offset"]), float(settings["y_offset"]))
        self.scope.viewing_angle = float(settings["view_angle"])
        print(f"Settings loaded from {SETTINGS_FILE}")

    def save_coord(self):
        with open(COORD_LOG, "a", encoding="utf-8") as f:
            log = f"{self.scope.get_time().utc_strftime('%Y-%m-%d %H:%M:%S')} - {self.scope.get_position()}\n"
            f.write(log)