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
