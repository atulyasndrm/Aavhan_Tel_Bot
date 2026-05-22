import os
import io
from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------
# PATH CONFIGURATION
# ----------------------------------------------------
# Base Directory: Points to your project root (Aavhan_Tel_Bot)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Asset Paths
CUSTOM_FONT_PATH = os.path.join(BASE_DIR, "assets", "custom_font.ttf")
MANDALA_PATH = os.path.join(BASE_DIR, "assets", "mandala.png")  # Fixed: Missing reference defined

def _get_font_safe(font_path, size):
    """
    Helper function to safely load custom fonts with a fallback 
    to standard default system font if the asset is missing.
    """
    try:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
    except Exception as e:
        print(f"Error loading custom font at {font_path}: {e}")
    
    # Fallback if custom font fails or doesn't exist
    return ImageFont.load_default()

def generate_job_image(job, theme="default"):
    # Dimensions and Theme Colors
    width, height = 800, 650
    
    if theme == "green":
        bg_color = "#F1F8E9"       # Light Green Background
        primary_color = "#4CAF50"  # Vibrant Green
        deep_color = "#1B5E20"     # Dark Forest Green
        header_text = "CONFIRMED PUJAN BOOKING"
        text_gold = "#D4AF37"      
        text_main = "#2D2D2D"
    elif theme == "red":
        bg_color = "#ECEFF1"       # Muted Gray Background
        primary_color = "#9E9E9E"  # Muted Gray Border
        deep_color = "#424242"     # Dark Gray Header
        header_text = "REJECTED BY YOU"
        text_gold = "#757575"      
        text_main = "#616161"      
    else:
        bg_color = "#FFF9F2"       # Default Background
        primary_color = "#FF9933"  # Saffron
        deep_color = "#800000"     # Maroon
        header_text = "SHUBH PUJAN INVITATION"
        text_gold = "#D4AF37"      
        text_main = "#2D2D2D"

    base = Image.new('RGB', (width, height), bg_color)
    
    # 1. Background Watermark / Mandala
    if os.path.exists(MANDALA_PATH):
        try:
            mandala = Image.open(MANDALA_PATH).convert("RGBA")
            m_size = 500
            mandala = mandala.resize((m_size, m_size), Image.Resampling.LANCZOS)
            
            # Reduce opacity to 10%
            alpha = mandala.split()[3]
            alpha = alpha.point(lambda p: int(p * 0.10))
            mandala.putalpha(alpha)
            
            # Paste the mandala in the center-bottom of the card
            offset = ((width - m_size) // 2, (height - m_size) // 2 + 50)
            base.paste(mandala, offset, mandala)
        except Exception as e:
            print(f"Failed to apply mandala background: {e}")

    draw = ImageDraw.Draw(base)

    # 2. Traditional Border
    border_thickness = 15
    draw.rectangle([10, 10, width-10, height-10], outline=primary_color, width=border_thickness)
    
    # 3. Header Setup
    draw.rectangle([15, 15, 785, 140], fill=deep_color)
    
    # Safely load font variants
    font_header = _get_font_safe(CUSTOM_FONT_PATH, 48)
    font_label = _get_font_safe(CUSTOM_FONT_PATH, 22)
    font_value = _get_font_safe(CUSTOM_FONT_PATH, 34)
    font_dakshina = _get_font_safe(CUSTOM_FONT_PATH, 42)

    # Render Header Text
    draw.text((width // 2, 75), header_text, font=font_header, fill="#FFFFFF", anchor="mm")

    # 4. Content Dynamic Layout
    y_offset = 200
    
    # Service Name
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

    # 5. Dakshina Section (Bottom Layout)
    draw.line([70, 500, 730, 500], fill=primary_color, width=2)
    
    draw.text((70, 530), "DAKSHINA", font=font_label, fill=text_gold)
    dakshina = job.get('fees', 'Swayam Iccha')
    draw.text((70, 565), f"₹ {dakshina}", font=font_dakshina, fill=deep_color)

    # Branding
    draw.text((600, 570), "AAVHAN", font=font_label, fill="#C43636")

    # Memory Buffer Export
    bio = io.BytesIO()
    base.save(bio, 'PNG')
    bio.seek(0)  # Reset pointer to start so the calling function can read it cleanly
    return bio.getvalue()