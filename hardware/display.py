from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm

class ScreenRenderer:
    WIDTH = 240
    HEIGHT = 240
    COLOR_BLACK = (0, 0, 0)
    COLOR_WHITE = (255, 255, 255)
    COLOR_GRAY = (100, 100, 100)
    BTN_COLOR = (60, 60, 60)
    BTN_SELECTED_COLOR = (140, 35, 35)
    FONT_PATH = fm.findfont(fm.FontProperties())
    def __init__(self):
        self.font = ImageFont.truetype(self.FONT_PATH, 14)
        self.small_font = ImageFont.truetype(self.FONT_PATH, 12)
        self.large_font = ImageFont.truetype(self.FONT_PATH, 24)

    def render_image_with_caption(self, image: Image.Image, caption: str) -> Image.Image:
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLOR_BLACK)
        draw = ImageDraw.Draw(img)
        img.paste(image, (0, 0))
        # Draw caption
        bbox = draw.textbbox((0, 0), caption, font=self.font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((1, 0), caption, font=self.font, fill=self.COLOR_GRAY)
        return img

    def render_menu(self, question: str, buttons: list, selected_idx: int) -> Image.Image:
        btn_height = 36
        btn_margin = 8

        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLOR_BLACK)
        draw = ImageDraw.Draw(img)
        # Draw question
        draw.text((10, 10), question, font=self.large_font, fill=self.COLOR_WHITE)
        
        # Draw buttons - all the same size now
        y = 50
        for idx, label in enumerate(buttons):
            rect = [20, y, self.WIDTH-20, y+btn_height]
            color = self.BTN_SELECTED_COLOR if idx == selected_idx else self.BTN_COLOR
            draw.rounded_rectangle(rect, radius=8, fill=color)
            bbox = draw.textbbox((0, 0), label, font=self.font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((self.WIDTH//2 - w//2, y + (btn_height-h)//2), label, font=self.font, fill=self.COLOR_WHITE)
            y += btn_height + btn_margin
        
        return img

    def render_settings(self, fields: dict, selected_idx: int) -> Image.Image:
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLOR_BLACK)
        draw = ImageDraw.Draw(img)
        
        # Draw back button
        back_rect = [10, 10, 70, 40]
        color = self.BTN_SELECTED_COLOR if selected_idx == 0 else self.BTN_COLOR
        draw.rounded_rectangle(back_rect, radius=8, fill=color)
        draw.text((20, 18), "< Back", font=self.small_font, fill=self.COLOR_WHITE)
        
        y = 60
        btn_height = 36
        btn_margin = 10
        
        for idx, (name, value) in enumerate(fields.items(), start=1):
            rect = [20, y, self.WIDTH-20, y+btn_height]
            color = self.BTN_SELECTED_COLOR if idx == selected_idx else self.BTN_COLOR
            draw.rounded_rectangle(rect, radius=8, fill=color)
            
            field_text = f"{name}: {value}"
            bbox = draw.textbbox((0, 0), field_text, font=self.font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            text_x = self.WIDTH//2 - w//2
            text_y = y + (btn_height-h)//2
            draw.text((text_x, text_y), field_text, font=self.font, fill=self.COLOR_WHITE)
            
            if idx == selected_idx: # Arrows
                if float(value) > 1:
                    draw.text((20, text_y), "←", font=self.font, fill=self.COLOR_WHITE)
                if float(value) < 10000:
                    draw.text((self.WIDTH - 30, text_y), "→", font=self.font, fill=self.COLOR_WHITE)

            y += btn_height + btn_margin
            
        return img

# Example usage:
#renderer = ScreenRenderer()
#img = renderer.render_menu("ASTROFLO MENU", ["Set Camera Offset", "Configure Telescope", "Navigate"], selected_idx=2)
#img.show()