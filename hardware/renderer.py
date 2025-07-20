""" Handles rendering of all UIs """
from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm

class ScreenRenderer:
    WIDTH = 240
    HEIGHT = 240
    COLOR_BLACK = (0, 0, 0)
    COLOR_WHITE = (255, 255, 255)
    COLOR_GRAY = (100, 255, 100)
    BTN_COLOR = (60, 60, 60)
    BTN_SELECTED_COLOR = (140, 35, 35)
    FONT_PATH = fm.findfont(fm.FontProperties())

    def __init__(self):
        self.font = ImageFont.truetype(self.FONT_PATH, 16)
        self.small_font = ImageFont.truetype(self.FONT_PATH, 12)
        self.large_font = ImageFont.truetype(self.FONT_PATH, 24)

    def _transform(self, img):
        return img.rotate(-90)
    

    def render_image_with_caption(self, image: Image.Image, top_caption: str, bot_caption: str = "") -> Image.Image:
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLOR_BLACK)
        draw = ImageDraw.Draw(img)
        img.paste(image, (0, 0))

        draw.text((1, 0), top_caption, font=self.font, fill=self.COLOR_GRAY)
        draw.text((1, self.HEIGHT - 20), bot_caption, font=self.font, fill=self.COLOR_GRAY)
        return self._transform(img)

    def render_menu(self, question: str, buttons: list, selected_idx: int, has_back: bool = False) -> Image.Image:
        btn_height = 36
        btn_margin = 8
        header_height = 50

        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLOR_BLACK)
        draw = ImageDraw.Draw(img)
                
        if has_back:
            back_rect = [10, 10, 70, 40]
            color = self.BTN_SELECTED_COLOR if selected_idx == 0 else self.BTN_COLOR
            draw.rounded_rectangle(back_rect, radius=8, fill=color)
            draw.text((20, 18), "< Back", font=self.small_font, fill=self.COLOR_WHITE)
        
        # Draw question - always at the top
        draw.text((120 if has_back else 10, 10), question, font=self.large_font, fill=self.COLOR_WHITE)
        
        # Calculate visible buttons based on selected index
        buttons_per_page = (self.HEIGHT - header_height) // (btn_height + btn_margin)
        start_idx = 0
        
        # Calculate which page of buttons to show based on the selected index
        if len(buttons) > buttons_per_page:
            page_number = selected_idx // buttons_per_page
            start_idx = page_number * buttons_per_page
        
        # Draw visible buttons
        y = header_height
        for i in range(min(buttons_per_page, len(buttons) - start_idx)):
            idx = i + start_idx + (1 if has_back else 0)
            label = buttons[idx - (1 if has_back else 0)]
            
            rect = [20, y, self.WIDTH-20, y+btn_height]
            color = self.BTN_SELECTED_COLOR if idx == selected_idx else self.BTN_COLOR
            draw.rounded_rectangle(rect, radius=8, fill=color)
            
            bbox = draw.textbbox((0, 0), str(label), font=self.font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((self.WIDTH//2 - w//2, y + (btn_height-h)//2), str(label),  
                    font=self.font, fill=self.COLOR_WHITE)
            
            y += btn_height + btn_margin
        
        # Draw scroll indicators if needed
        if len(buttons) > buttons_per_page:
            current_page = selected_idx // buttons_per_page
            total_pages = (len(buttons) + buttons_per_page - 1) // buttons_per_page
            
            # Show page indicator
            page_text = f"{current_page + 1}/{total_pages}"
            bbox = draw.textbbox((0, 0), page_text, font=self.small_font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((self.WIDTH - w - 2, 2), page_text, font=self.small_font, fill=self.COLOR_WHITE)
            
            # Up arrow if not on first page
            if current_page > 0:
                draw.text((self.WIDTH - 30, header_height), "▲", font=self.font, fill=self.COLOR_WHITE)
            
            # Down arrow if not on last page
            if current_page < total_pages - 1:
                draw.text((self.WIDTH - 30, self.HEIGHT - 30), "▼", font=self.font, fill=self.COLOR_WHITE)
        
        return self._transform(img)

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
            
        return self._transform(img)
    
    def render_many_text(self, texts: list) -> Image.Image:
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLOR_BLACK)
        draw = ImageDraw.Draw(img)
        
        y = 10
        for text in texts:
            bbox = draw.textbbox((0, 0), text, font=self.font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((self.WIDTH//2 - w//2, y), text, font=self.font, fill=self.COLOR_WHITE)
            y += h + 5
        
        return self._transform(img)