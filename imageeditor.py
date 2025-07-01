from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ---------- CONFIG -----------------------------------------------------------
INPUT_FILE   = Path("boxwork.png")
OUTPUT_FILE  = Path("boxwork_postcard.png")

DPI          = 300
WIDTH_IN     = 4            # inches (width)
HT_IN        = 6            # inches (height) – portrait
CREAM        = (245, 245, 220)
BORDER_IN    = 0.05         # inches
CAPTION_TEXT = "Wind Cave National Park"

CANDIDATE_FONTS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
]
# -----------------------------------------------------------------------------

# Derived pixel dimensions
W_PX, H_PX = int(WIDTH_IN * DPI), int(HT_IN * DPI)
BORDER_PX  = int(BORDER_IN * DPI)

# ---------- HELPERS ----------------------------------------------------------
def get_font(size: int) -> ImageFont.ImageFont:
    for path in CANDIDATE_FONTS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()

def text_dims(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    """Return (width, height) of text with current Pillow (≥10) API."""
    x0, y0, x1, y1 = draw.textbbox((0, 0), text, font=font)
    return x1 - x0, y1 - y0

def fit_font(draw, text, max_w, max_h):
    lo, hi = 8, 500
    while lo < hi:
        mid  = (lo + hi + 1) // 2
        font = get_font(mid)
        w, h = text_dims(draw, text, font)
        if w <= max_w and h <= max_h:
            lo = mid
        else:
            hi = mid - 1
    return get_font(lo)

def largest_crop(img: Image.Image, target_ratio: float) -> Image.Image:
    w, h = img.size
    if w / h > target_ratio:                  # too wide → crop width
        new_w = int(h * target_ratio)
        left  = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = int(w / target_ratio)             # too tall → crop height
    top   = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))
# -----------------------------------------------------------------------------

def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    img = Image.open(INPUT_FILE).convert("RGB")
    img = largest_crop(img, WIDTH_IN / HT_IN)

    inner_w, inner_h = W_PX - 2 * BORDER_PX, H_PX - 2 * BORDER_PX
    img = img.resize((inner_w, inner_h), resample=Image.NEAREST)


    canvas = Image.new("RGB", (W_PX, H_PX), CREAM)
    canvas.paste(img, (BORDER_PX, BORDER_PX))

    draw          = ImageDraw.Draw(canvas)
    caption_max_h = int(0.10 * H_PX)
    font          = fit_font(draw, CAPTION_TEXT, inner_w, caption_max_h)
    text_w, text_h = text_dims(draw, CAPTION_TEXT, font)

    x = (W_PX - text_w) // 2
    y = H_PX - BORDER_PX - text_h            # rest on bottom border
    draw.text((x, y), CAPTION_TEXT, fill=CREAM, font=font)

    canvas.save(OUTPUT_FILE, dpi=(DPI, DPI))
    print(f"✅  Saved {OUTPUT_FILE}  ({W_PX}×{H_PX}px @ {DPI} dpi)")

if __name__ == "__main__":
    main()
