""" Real 1.3" Adafruit TFT Bonnet (ST7789 display + 7 buttons). Pi only: imported lazily by backends.py. """
import board
from digitalio import DigitalInOut, Direction
from adafruit_rgb_display import st7789
from PIL import Image, ImageDraw

BUTTON_PINS = {"A": board.D5, "B": board.D6, "L": board.D27, "R": board.D23, "U": board.D17, "D": board.D22, "C": board.D4}


class TFTDisplay:
    BAUDRATE = 24000000

    def __init__(self):
        self.disp = st7789.ST7789(
            board.SPI(),
            height=240,
            y_offset=80,
            rotation=180,
            cs=DigitalInOut(board.CE0),
            dc=DigitalInOut(board.D25),
            rst=DigitalInOut(board.D24),
            baudrate=self.BAUDRATE,
        )
        self.buttons = {}
        for name, pin in BUTTON_PINS.items():
            button = DigitalInOut(pin)
            button.direction = Direction.INPUT
            self.buttons[name] = button

        self.backlight = DigitalInOut(board.D26)
        self.backlight.switch_to_output()
        self.backlight.value = True

        self.width = self.disp.width
        self.height = self.disp.height
        self.image = Image.new("RGBA", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        self.brightness = 0
        self.overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, self.brightness))

    # inverted to make more logical sense, 0: Full brightness, 1: HIGHEST
    def set_brightness(self, b: float):
        b = max(0.0, min(1.0, b))
        self.brightness = int((1.0 - b) * 255)
        self.overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, self.brightness))

    def set_backlight(self, on: bool):
        self.backlight.value = bool(on)

    def clear(self):
        self.disp.image(Image.new("RGB", (self.width, self.height), (0, 0, 0)))

    def draw_screen(self, img):
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=(0, 0, 0))
        if img is not None:
            resize = img.resize((240, 240))
            self.image.paste(resize, (0, 0))
            self.image = Image.alpha_composite(self.image, self.overlay)
        self.disp.image(self.image)

    def read_buttons(self, last_input):
        """ Buttons are active-low """
        b = self.buttons
        last_input.update(not b["A"].value, not b["B"].value, not b["L"].value, not b["R"].value,
                          not b["U"].value, not b["D"].value, not b["C"].value)
