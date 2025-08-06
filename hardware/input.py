""" Basic Input Manager for 1.3" Adafruit TFT Bonnet """
class Input:

    controls = {}

    def __init__(self):
        self.reset()

    def handle(self, control, value):
        if control["press"] is not None and not control["state"] and value: # Pressed
            control["press"]()
        elif control["release"] is not None and control["state"] and not value: #Released
            control["release"]()
        elif control["hold"] is not None and value: # Held
            control["hold"]()

        control["state"] = value

    def update(self, a, b, l, r, u, d, c): 
        ct = self.controls
        self.handle(ct['A'], a)
        self.handle(ct['B'], b)
        self.handle(ct['L'], l)
        self.handle(ct['R'], r)
        self.handle(ct['U'], u)
        self.handle(ct['D'], d)
        self.handle(ct['C'], c)

    def reset(self):
        self.controls = {
            'A': {
                "state": False,
                "press": None,
                "release": None,
                "hold": None
            },
            'B': {
                "state": False,
                "press": None,
                "release": None,
                "hold": None
            },
            'L': {
                "state": False,
                "press": None,
                "release": None,
                "hold": None
            },
            'R': {
                "state": False,
                "press": None,
                "release": None,
                "hold": None
            },
            'U': {
                "state": False,
                "press": None,
                "release": None,
                "hold": None
            },
            'D': {
                "state": False,
                "press": None,
                "release": None,
                "hold": None
            },
            'C': {
                "state": False,
                "press": None,
                "release": None,
                "hold": None
            }
        }