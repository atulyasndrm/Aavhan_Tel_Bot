import os
from PIL import Image, ImageDraw, ImageFont
import io
import urllib.request
import tempfile

# Get the absolute path to the project root (2 levels up from app/services/image_service.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CUSTOM_FONT_PATH = os.path.join(BASE_DIR, "assets", "custom_font.ttf")
MANDALA_PATH = os.path.join(BASE_DIR, "assets", "mandala.png")
FALLBACK_FONT_PATH = os.path.join(tempfile.gettempdir(), "NotoSerif-Regular.ttf")

def get_font(size):
    """Helper to reliably load a TrueType font, downloading a fallback if necessary."""
    try:
        return ImageFont.truetype(CUSTOM_FONT_PATH, size)
    except IOError:
        if not os.path.exists(FALLBACK_FONT_PATH):
            try:
                # Download Google's Noto Serif font dynamically for a traditional look
                url = "https://raw.githubusercontent.com/google/fonts/main/ofl/notoserif/NotoSerif-Regular.ttf"
                urllib.request.urlretrieve(url, FALLBACK_FONT_PATH)
            except Exception as e:
                print(f"Font download failed: {e}")
        try:
            return ImageFont.truetype(FALLBACK_FONT_PATH, size)
        except IOError:
            return ImageFont.load_default()

def generate_job_image(job, theme="default"):
    # Dimensions and "Pavitra" Colors
    width, height = 800, 650
    
    if theme == "green":
        bg_color = "#F1F8E9"      # Light Green Background
        primary_color = "#4CAF50" # Vibrant Green
        deep_color = "#1B5E20"    # Dark Forest Green
        header_text = "CONFIRMED PUJAN BOOKING"
        text_gold = "#D4AF37"      
        text_main = "#2D2D2D"
    elif theme == "red":
        bg_color = "#ECEFF1"      # Muted Gray Background
        primary_color = "#9E9E9E" # Muted Gray Border
        deep_color = "#424242"    # Dark Gray Header
        header_text = "REJECTED BY YOU"
        text_gold = "#757575"     # Muted Text
        text_main = "#616161"     # Muted Text
    else:
        bg_color = "#FFF9F2"      # Default Pavitra Background
        primary_color = "#FF9933" # Saffron
        deep_color = "#800000"    # Maroon
        header_text = "SHUBH PUJAN INVITATION"
        text_gold = "#D4AF37"      
        text_main = "#2D2D2D"

    base = Image.new('RGB', (width, height), bg_color)
    
    # Optional: Add a subtle mandala/texture background if the image exists
    if os.path.exists(MANDALA_PATH):
        try:
            mandala = Image.open(MANDALA_PATH).convert("RGBA")
            # Resize texture to fit nicely within the card
            m_size = 500
            mandala = mandala.resize((m_size, m_size), Image.Resampling.LANCZOS)
            
            # Reduce opacity to 10% so it acts as a subtle watermark
            alpha = mandala.split()[3]
            alpha = alpha.point(lambda p: p * 0.10)
            mandala.putalpha(alpha)
            
            # Paste the mandala in the center-bottom of the card
            offset = ((width - m_size) // 2, (height - m_size) // 2 + 50)
            base.paste(mandala, offset, mandala)
        except Exception as e:
            print(f"Failed to apply mandala background: {e}")

    draw = ImageDraw.Draw(base)

    # 1. Traditional Border
    border_thickness = 15
    draw.rectangle([10, 10, width-10, height-10], outline=primary_color, width=border_thickness)
    
    # 2. Header with Traditional Flare
    draw.rectangle([15, 15, 785, 140], fill=deep_color)
    
    # Load fonts using the robust helper
    font_header = get_font(48)
    font_label = get_font(22)
    font_value = get_font(34)
    font_dakshina = get_font(42)

    # Header Text
    draw.text((width//2, 75), header_text, font=font_header, fill="#FFFFFF", anchor="mm")

    # 3. Content Layout
    y_offset = 200
    
    # Service Name (e.g., Satyanarayan Katha, Griha Pravesh)
    draw.text((70, y_offset), "PUJA", font=font_label, fill=text_gold)
    pujan_name = str(job.get('title', 'Vishesh Puja')).upper()
    draw.text((70, y_offset + 35), pujan_name, font=font_value, fill=deep_color)

    # Date & Time
    draw.text((70, y_offset + 130), "MUHURAT DATE & TIME", font=font_label, fill=text_gold)
    datetime_text = f"{job.get('date', 'As per Muhurat')}  {job.get('time', '')}".strip()
    draw.text((70, y_offset + 165), datetime_text, font=font_value, fill=text_main)

    # Location
    draw.text((450, y_offset + 130), "STHAN (LOCATION)", font=font_label, fill=text_gold)
    draw.text((450, y_offset + 165), str(job.get('location', 'Yajman House')), font=font_value, fill=text_main)

    # 4. Dakshina Section (Bottom)
    draw.line([70, 500, 730, 500], fill=primary_color, width=2)
    
    draw.text((70, 530), "DAKSHINA", font=font_label, fill=text_gold)
    dakshina = job.get('fees', 'Swayam Iccha')
    draw.text((70, 565), f"₹ {dakshina}", font=font_dakshina, fill=deep_color)

    # Branding / App Name
    draw.text((600, 570), "AAVHAN", font=font_label, fill="#C43636")

    # Export
    bio = io.BytesIO()
    bio.name = 'pujan_card.png'
    base.save(bio, 'PNG')
    return bio.getvalue()