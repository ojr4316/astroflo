""" Handles rendering of all UIs """
from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm

WIDTH = 240
HEIGHT = 240
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (100, 255, 100)
BTN_COLOR = (60, 60, 60)
BTN_SELECTED_COLOR = (140, 35, 35)
FONT_PATH = fm.findfont(fm.FontProperties())

font = ImageFont.truetype(FONT_PATH, 16)
small_font = ImageFont.truetype(FONT_PATH, 12)
large_font = ImageFont.truetype(FONT_PATH, 24)

def _transform(img): # match orientation of the physical screen # TODO: implement at other layer?
    return img.rotate(-90)

def render_image_with_caption(image: Image.Image, top_caption: str, bot_caption: str = "") -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_BLACK)
    draw = ImageDraw.Draw(img)
    img.paste(image, (0, 0))

    draw.text((1, 0), top_caption, font=font, fill=COLOR_GRAY)
    draw.text((1, HEIGHT - 20), bot_caption, font=font, fill=COLOR_GRAY)
    return _transform(img)

def render_menu(question: str, buttons: list, selected_idx: int, has_back: bool = False) -> Image.Image:
    btn_height = 36
    btn_margin = 8
    header_height = 50

    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_BLACK)
    draw = ImageDraw.Draw(img)
            
    if has_back:
        back_rect = [10, 10, 70, 40]
        color = BTN_SELECTED_COLOR if selected_idx == 0 else BTN_COLOR
        draw.rounded_rectangle(back_rect, radius=8, fill=color)
        draw.text((20, 18), "< Back", font=small_font, fill=COLOR_WHITE)
    
    # Draw question - always at the top
    draw.text((120 if has_back else 10, 10), question, font=large_font, fill=COLOR_WHITE)
    
    # Calculate visible buttons based on selected index
    buttons_per_page = (HEIGHT - header_height) // (btn_height + btn_margin)
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
        
        rect = [20, y, WIDTH-20, y+btn_height]
        color = BTN_SELECTED_COLOR if idx == selected_idx else BTN_COLOR
        draw.rounded_rectangle(rect, radius=8, fill=color)
        
        bbox = draw.textbbox((0, 0), str(label), font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((WIDTH//2 - w//2, y + (btn_height-h)//2), str(label),  
                font=font, fill=COLOR_WHITE)
        
        y += btn_height + btn_margin
    
    # Draw scroll indicators if needed
    if len(buttons) > buttons_per_page:
        current_page = selected_idx // buttons_per_page
        total_pages = (len(buttons) + buttons_per_page - 1) // buttons_per_page
        
        # Show page indicator
        page_text = f"{current_page + 1}/{total_pages}"
        bbox = draw.textbbox((0, 0), page_text, font=small_font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((WIDTH - w - 2, 2), page_text, font=small_font, fill=COLOR_WHITE)
        
        # Up arrow if not on first page
        if current_page > 0:
            draw.text((WIDTH - 30, header_height), "▲", font=font, fill=COLOR_WHITE)
        
        # Down arrow if not on last page
        if current_page < total_pages - 1:
            draw.text((WIDTH - 30, HEIGHT - 30), "▼", font=font, fill=COLOR_WHITE)
    
    return _transform(img)

def render_settings(fields: dict, selected_idx: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_BLACK)
    draw = ImageDraw.Draw(img)
    
    # Draw back button
    back_rect = [10, 10, 70, 40]
    color = BTN_SELECTED_COLOR if selected_idx == 0 else BTN_COLOR
    draw.rounded_rectangle(back_rect, radius=8, fill=color)
    draw.text((20, 18), "< Back", font=small_font, fill=COLOR_WHITE)
    
    y = 60
    btn_height = 36
    btn_margin = 10
    
    for idx, (name, value) in enumerate(fields.items(), start=1):
        rect = [20, y, WIDTH-20, y+btn_height]
        color = BTN_SELECTED_COLOR if idx == selected_idx else BTN_COLOR
        draw.rounded_rectangle(rect, radius=8, fill=color)
        
        field_text = f"{name}: {value}"
        bbox = draw.textbbox((0, 0), field_text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        text_x = WIDTH//2 - w//2
        text_y = y + (btn_height-h)//2
        draw.text((text_x, text_y), field_text, font=font, fill=COLOR_WHITE)
        
        if idx == selected_idx: # Arrows
            if float(value) > 1:
                draw.text((20, text_y), "←", font=font, fill=COLOR_WHITE)
            if float(value) < 10000:
                draw.text((WIDTH - 30, text_y), "→", font=font, fill=COLOR_WHITE)

        y += btn_height + btn_margin
        
    return _transform(img)

def render_many_text(texts: list) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_BLACK)
    draw = ImageDraw.Draw(img)
    
    y = 10
    for text in texts:
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((WIDTH//2 - w//2, y), text, font=font, fill=COLOR_WHITE)
        y += h + 5
    
    return _transform(img)