import io
import random
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

# Palette of contrasting background colors to make text readable
_BACKGROUND_COLORS = [
    (35, 132, 188),
    (83, 99, 181),
    (212, 163, 115),
    (32, 125, 90),
    (180, 83, 97)
]

_FONT_SIZE = 64
_FONT_CANDIDATES = [
    "DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",
    "Arial.ttf",
    "arial.ttf",
    "FreeSans.ttf"
]


def _load_font() -> ImageFont.ImageFont:
    for name in _FONT_CANDIDATES:
        # Try system lookup via Pillow
        try:
            return ImageFont.truetype(name, _FONT_SIZE)
        except OSError:
            pass

        # Try bundled Pillow fonts directory
        pil_fonts_dir = Path(ImageFont.__file__).resolve().parent / "fonts"
        font_path = pil_fonts_dir / name
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), _FONT_SIZE)
            except OSError:
                continue

    return ImageFont.load_default()


def generate_captcha_image(label: str) -> Tuple[bytes, str]:
    """
    Generates an in-memory PNG image that contains the label (e.g. captcha answer).
    Returns the PNG bytes and a filename hint for Telegram uploads.
    """
    width, height = 520, 220
    background = random.choice(_BACKGROUND_COLORS)

    # Split emoji and name to avoid unreadable glyphs when emoji font is missing.
    _, _, fruit_name = label.partition(" ")
    text = fruit_name or label

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)

    font = _load_font()

    # Measure text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    if not hasattr(font, "path"):
        # Fallback font is tiny; upscale rendered glyphs to keep captcha readable.
        scale_factor = 6
        mask = Image.new("L", (text_width, text_height))
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((0, 0), text, font=font, fill=255)
        mask = mask.resize(
            (mask.width * scale_factor, mask.height * scale_factor),
            resample=Image.NEAREST
        )
        text_width, text_height = mask.size
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        shadow_offset = 4
        shadow = mask.copy()
        image.paste((0, 0, 0), (x + shadow_offset, y + shadow_offset), shadow)
        image.paste((255, 255, 255), (x, y), mask)
    else:
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        shadow_offset = 4
        draw.text((x + shadow_offset, y + shadow_offset), text, fill=(0, 0, 0), font=font)
        draw.text((x, y), text, fill=(255, 255, 255), font=font)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read(), "captcha.png"
