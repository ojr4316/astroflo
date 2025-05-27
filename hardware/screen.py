""" Screen Manager for 1.3" Adafruit TFT Bonnet """
import os
from utils import is_pi
if is_pi():
    import time
    import random
    from colorsys import hsv_to_rgb
    import board
    from digitalio import DigitalInOut, Direction
    from PIL import Image, ImageDraw, ImageFont
    from adafruit_rgb_display import st7789

    class Screen:
        cs_pin = DigitalInOut(board.CE0)
        dc_pin = DigitalInOut(board.D25)
        reset_pin = DigitalInOut(board.D24)
        BAUDRATE = 24000000

        spi = board.SPI()
        disp = st7789.ST7789(
            spi,
            height=240,
            y_offset=80,
            rotation=180,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=BAUDRATE,
        )

        # Input pins:
        button_A = DigitalInOut(board.D5)
        button_A.direction = Direction.INPUT

        button_B = DigitalInOut(board.D6)
        button_B.direction = Direction.INPUT

        button_L = DigitalInOut(board.D27)
        button_L.direction = Direction.INPUT

        button_R = DigitalInOut(board.D23)
        button_R.direction = Direction.INPUT

        button_U = DigitalInOut(board.D17)
        button_U.direction = Direction.INPUT

        button_D = DigitalInOut(board.D22)
        button_D.direction = Direction.INPUT

        button_C = DigitalInOut(board.D4)
        button_C.direction = Direction.INPUT

        backlight = DigitalInOut(board.D26)
        backlight.switch_to_output()
        backlight.value = True

        width = disp.width
        height = disp.height
        image = Image.new("RGBA", (width, height))

        draw = ImageDraw.Draw(image)

        fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)

        frame = 0

        brightness = 0

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, brightness))

        # inverted to make more logical sense, 0: Full brightness, 1: HIGHEST
        def set_brightness(self, b: int):
            b = max(0.0, min(1.0, b))
            self.brightness = int((1.0 - b) * 255)
            print(self.brightness)
            self.overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, self.brightness))

        def draw_screen(self, img):
            self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=(0, 0, 0))

            if img is not None:
                resize = img.resize((240, 240))
                self.image.paste(resize, (0, 0))
                self.image = Image.alpha_composite(self.image, self.overlay)
            self.disp.image(self.image)        

        def handle_input(self, input):
            input.update(not self.button_A.value, not self.button_B.value, not self.button_L.value, not self.button_R.value, not self.button_U.value, not self.button_D.value, not self.button_C.value)




else: # Fake Screen

    class Screen:

        def __init__(self):
            self.width = 240
            self.height = 240
            #self.image = Image.new("RGB", (self.width, self.height))
        def set_brightness(self, b): pass