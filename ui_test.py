from astronomy.Telescope import Telescope
from hardware.ui import UIManager, ScreenState

if __name__ == "__main__":
    scope = Telescope(
        aperature=200,
        focal_length=1200,
        eyepiece=25,
        eyepiece_fov=40,)
    ui = UIManager(scope)
    ui.state = ScreenState.TARGET_SELECT

    img = ui.render()
    img.show()