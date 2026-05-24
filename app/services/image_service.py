# ============================================================
# TELEGRAM JOB INVITATION IMAGE
# ============================================================

import io
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# IMAGE SIZE
# ============================================================

WIDTH = 1440
HEIGHT = 1080

# ============================================================
# FONT LOADER
# ============================================================

def load_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    ]

    for font_name in candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue

    return ImageFont.load_default()


# ============================================================
# TEXT WRAPPER
# ============================================================

def wrap_text(draw, text, font, max_width):
    words = str(text).split()
    if not words:
        return []

    lines = []
    current = words[0]

    for word in words[1:]:
        test = f"{current} {word}"
        width = draw.textbbox((0, 0), test, font=font)[2]
        if width <= max_width:
            current = test
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


# ============================================================
# MAIN FUNCTION
# ============================================================

def generate_job_image(job, theme="default"):
    THEMES = {
        "default": {
            "bg": "#FFF9F2",
            "frame": "#F97316",
            "header": "#7C2D12",
            "title": "SHUBH PUJAN INVITATION",
            "soft": "#D97706",
            "main": "#111827",
            "accent": "#B91C1C"
        },
        "green": {
            "bg": "#F7FBF3",
            "frame": "#F97316",
            "header": "#2E7D32",
            "title": "PUJAN BOOKING",
            "soft": "#166534",
            "main": "#111827",
            "accent": "#166534"
        },
        "red": {
            "bg": "#E5E7EB",
            "frame": "#6B7280",
            "header": "#374151",
            "title": "PUJAN UPDATE",
            "soft": "#374151",
            "main": "#111827",
            "accent": "#B91C1C"
        }
    }

    theme = THEMES.get(theme, THEMES["default"])

    img = Image.new("RGB", (WIDTH, HEIGHT), theme["bg"])
    draw = ImageDraw.Draw(img)

    draw.rectangle([20, 20, WIDTH - 20, HEIGHT - 20], outline=theme["frame"], width=28)
    draw.rectangle([20, 20, WIDTH - 20, 260], fill=theme["header"])
    draw.rectangle([40, 240, WIDTH - 40, HEIGHT - 40], fill="white")

    header_font = load_font(56, bold=True)
    label_font = load_font(28)
    value_font = load_font(48, bold=True)
    value_large_font = load_font(48, bold=True)
    footer_font = load_font(40, bold=True)

    draw.text((WIDTH // 2, 120), theme["title"], font=header_font, fill="white", anchor="mm")

    ceremony = str(job.get("title") or job.get("ceremony_type") or job.get("ceremonyType") or "Vishesh Puja").upper()
    muhurat_date = str(job.get('date') or 'As per Muhurat')
    muhurat_time = str(job.get('time') or '')
    location = f"{job.get('city') or ''}, {job.get('state') or ''}".strip(', ').strip() or str(job.get('location') or 'Yajman House')
    dakshina = job.get('fees', 'To be discussed')
    dakshina_text = f"₹ {dakshina}" if any(c.isdigit() for c in str(dakshina)) else str(dakshina)

    inner_left = 90
    inner_right = 820
    content_top = 320

    draw.text((inner_left, content_top), "PUJA", font=label_font, fill=theme["soft"])
    draw.text((inner_left, content_top + 42), ceremony, font=value_large_font, fill=theme["main"])

    location_y = content_top + 180
    draw.text((inner_left, location_y), "STHAN (LOCATION)", font=label_font, fill=theme["soft"])
    draw.text((inner_left, location_y + 42), location, font=value_font, fill=theme["main"])

    right_y = content_top
    draw.text((inner_right, right_y), "MUHURAT DATE & TIME", font=label_font, fill=theme["soft"])
    draw.text((inner_right, right_y + 42), muhurat_date, font=value_font, fill=theme["main"])
    draw.text((inner_right, right_y + 110), muhurat_time, font=value_font, fill=theme["main"])

    divider_y = 760
    draw.line([inner_left, divider_y, WIDTH - inner_left, divider_y], fill=theme["frame"], width=4)

    draw.text((inner_left, divider_y + 50), "DAKSHINA", font=label_font, fill=theme["soft"])
    draw.text((inner_left, divider_y + 110), dakshina_text, font=value_large_font, fill=theme["main"])
    draw.text((WIDTH - inner_left, divider_y + 110), "AAHVAN", font=footer_font, fill=theme["accent"], anchor="rm")

    bio = io.BytesIO()
    img.save(bio, format="PNG", optimize=True)
    bio.seek(0)
    return bio.getvalue()


# ============================================================
# PRIEST PORTFOLIO / BUSINESS CARD
# ============================================================

def generate_portfolio_card(user, completed_count):
    width, height = 1080, 640
    img = Image.new("RGB", (width, height), "#FFF9F2")
    draw = ImageDraw.Draw(img)
    
    # Draw outer border and header
    draw.rectangle([0, 0, width, height], outline="#F97316", width=15)
    draw.rectangle([0, 0, width, 140], fill="#F97316")
    
    # Fonts
    header_font = load_font(50, bold=True)
    name_font = load_font(70, bold=True)
    text_font = load_font(38)
    badge_font = load_font(32, bold=True)
    
    # Header Text
    draw.text((width // 2, 70), "AAVHAN VERIFIED PANDIT", font=header_font, fill="white", anchor="mm")
    
    # User Details
    name = str(user.get("name") or "Pandit Ji").upper()
    phone = str(user.get("phone") or "N/A")
    pid = str(user.get("id"))
    
    created_val = user.get("created_at")
    joined = created_val.strftime('%B %Y') if created_val else "N/A"
    
    # Write Content
    draw.text((80, 200), name, font=name_font, fill="#111827")
    draw.text((80, 310), f"Priest ID:   {pid}", font=text_font, fill="#4B5563")
    draw.text((80, 380), f"Contact:     {phone}", font=text_font, fill="#4B5563")
    draw.text((80, 450), f"Joined:        {joined}", font=text_font, fill="#4B5563")
    
    # Draw Badges (Rounded Pills)
    # Verified Badge
    draw.rounded_rectangle([80, 520, 380, 590], radius=35, fill="#ECFCCB", outline="#22C55E", width=4)
    draw.text((230, 555), "✅ VERIFIED", font=badge_font, fill="#166534", anchor="mm")
    
    # Completed Pujas Badge
    draw.rounded_rectangle([410, 520, 1000, 590], radius=35, fill="#FFF7ED", outline="#F97316", width=4)
    draw.text((705, 555), f"🌟 {completed_count} PUJAS COMPLETED", font=badge_font, fill="#9A3412", anchor="mm")
    
    # Export
    bio = io.BytesIO()
    img.save(bio, format="PNG", optimize=True)
    bio.seek(0)
    return bio.getvalue()
