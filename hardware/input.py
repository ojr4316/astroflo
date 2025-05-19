""" Basic Input Manager for 1.3" Adafruit TFT Bonnet """
class Input:

    controls = {
        'A': {
            "state": False,
            "press": None,
            "release": None
        },
        'B': {
            "state": False,
            "press": None,
            "release": None
        },
        'L': {
            "state": False,
            "press": None,
            "release": None
        },
        'R': {
            "state": False,
            "press": None,
            "release": None
        },
        'U': {
            "state": False,
            "press": None,
            "release": None
        },
        'D': {
            "state": False,
            "press": None,
            "release": None
        },
        'C': {
            "state": False,
            "press": None,
            "release": None
        }
    }

    def handle(self, control, value):
        if control["press"] is not None and not control["state"] and value: # Pressed
            control["press"]()
        elif control["release"] is not None and control["state"] and not value: #Released
            control["release"]()
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
