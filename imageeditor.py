#!/usr/bin/env python3
"""
Make a 4×6‑inch (300 dpi) postcard with:
• cream border
• optional gradient shadow at bottom (drawn **behind** the border)
• caption with user‑controlled font / position / alignment
The original iPhone HDR PNG is tone‑mapped to sRGB by macOS `sips`.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess, sys
from PIL import (
    Image, ImageDraw, ImageFont,
    ImageOps
)

# ────────── CONFIG ───────────────────────────────────────────────────────────
INPUT_FILE        = Path("boxwork.png")
OUTPUT_FILE       = Path("boxwork_postcard.tif")

# postcard geometry
DPI               = 300
WIDTH_IN, HT_IN   = 4, 6              # inches (portrait)
BORDER_IN         = 0.1              # inches
CREAM             = (245, 245, 220)   # border colour

# caption
CAPTION_TEXT      = "Wind Cave National Park"
CAPTION_POS       = "bottom"          # "bottom" or "top"
CAPTION_ALIGN     = "left"          # "center" | "left" | "right"
CAPTION_OFFSET_PX = -75                 # +ve moves text up (bottom) / down (top)

# font – set explicit path to Ironick NF (adjust if installed elsewhere)
FONT_PATH         = "/Users/monicagraham/Downloads/Fonts/IronickNF.otf"
FALLBACK_FONTS    = [
    FONT_PATH,  # still try Ironick first via fallback in case FONT_PATH is None
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
]

# gradient shadow (drawn only inside the photo area, not over the border)
ADD_SHADOW          = True            # toggle shadow on/off
SHADOW_COLOR        = (0, 0, 0)       # base colour of shadow
SHADOW_OPACITY      = 0.50            # 0‑1 darkest opacity at bottom edge
SHADOW_HEIGHT_FRAC  = 0.25            # fraction of inner‑photo height
# ─────────────────────────────────────────────────────────────────────────────


# ────────── HELPERS ─────────────────────────────────────────────────────────

def run_sips_to_srgb(src: Path, dst: Path):
    """Tone‑map wide‑gamut/HDR → 16‑bit sRGB via macOS `sips`."""
    cmd = [
        "sips",
        "--matchTo", "/System/Library/ColorSync/Profiles/sRGB Profile.icc",
        str(src), "--out", str(dst),
    ]
    subprocess.run(cmd, check=True)


def pick_font(pt):
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, pt)
        except OSError:
            pass  # fall back if explicit path failed
    for p in FALLBACK_FONTS:
        try:
            return ImageFont.truetype(p, pt)
        except OSError:
            continue
    return ImageFont.load_default()


def text_dims(draw, text, font):
    x0, y0, x1, y1 = draw.textbbox((0, 0), text, font=font)
    return x1 - x0, y1 - y0


def fit_font(draw, text, max_w, max_h):
    lo, hi = 6, 600
    while lo < hi:
        mid  = (lo + hi + 1) // 2
        font = pick_font(mid)
        if max(text_dims(draw, text, font)) <= max(max_w, max_h):
            lo = mid
        else:
            hi = mid - 1
    return pick_font(lo)


def largest_crop(img, ratio):
    w, h = img.size
    if w / h > ratio:
        nw   = int(h * ratio)
        left = 0.5 * (w - nw)
        return img.crop((left, 0, left + nw, h))
    nh  = int(w / ratio)
    top = 0.5 * (h - nh)
    return img.crop((0, top, w, top + nh))


# ────────────────────────────────────────────────────────────────────────────

def add_shadow_gradient(base: Image.Image, border_px: int):
    """Paste a vertical alpha gradient behind the inner‑photo area (leaving border untouched)."""
    if not ADD_SHADOW or SHADOW_OPACITY <= 0 or SHADOW_HEIGHT_FRAC <= 0:
        return base

    w, h      = base.size
    inner_w   = w - 2 * border_px
    inner_h   = h - 2 * border_px
    grad_h    = int(inner_h * SHADOW_HEIGHT_FRAC)

    # build 1‑pixel‑wide alpha ramp
    ramp = Image.new("L", (1, grad_h))
    for y in range(grad_h):
        alpha = int(SHADOW_OPACITY * 255 * (y / (grad_h - 1)))
        ramp.putpixel((0, y), alpha)
    alpha_band = ramp.resize((inner_w, grad_h))

    shadow = Image.new("RGBA", (inner_w, grad_h), SHADOW_COLOR + (0,))
    shadow.putalpha(alpha_band)

    base_rgba = base.convert("RGBA")
    paste_y   = border_px + inner_h - grad_h
    base_rgba.paste(shadow, (border_px, paste_y), shadow)
    return base_rgba.convert("RGB")


# ────────────────────────────────────────────────────────────────────────────

def main():
    if not INPUT_FILE.exists():
        sys.exit("❌  input image not found")

    # 1️⃣  Tone‑map → sRGB PNG (tmp)
    with NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    run_sips_to_srgb(INPUT_FILE, tmp_path)

    # 2️⃣  Rotate & crop to postcard aspect
    img = ImageOps.exif_transpose(Image.open(tmp_path))
    img = largest_crop(img, WIDTH_IN / HT_IN)

    W_PX, H_PX = int(WIDTH_IN * DPI), int(HT_IN * DPI)
    BORDER_PX  = int(BORDER_IN * DPI)
    inner_w, inner_h = W_PX - 2 * BORDER_PX, H_PX - 2 * BORDER_PX
    img = img.resize((inner_w, inner_h), resample=Image.BOX)

    # 3️⃣  Canvas + border
    canvas = Image.new("RGB", (W_PX, H_PX), CREAM)
    canvas.paste(img, (BORDER_PX, BORDER_PX))

    # 4️⃣  Gradient shadow (inside photo area, behind border)
    canvas = add_shadow_gradient(canvas, BORDER_PX)

    # 5️⃣  Caption
    draw = ImageDraw.Draw(canvas)
    font = fit_font(draw, CAPTION_TEXT, inner_w, int(0.10 * H_PX))
    tw, th = text_dims(draw, CAPTION_TEXT, font)

    if CAPTION_ALIGN == "center":
        tx = (W_PX - tw) // 2
    elif CAPTION_ALIGN == "left":
        tx = BORDER_PX
    else:  # "right"
        tx = W_PX - BORDER_PX - tw

    if CAPTION_POS == "bottom":
        ty = H_PX - BORDER_PX - th + CAPTION_OFFSET_PX
    else:  # "top"
        ty = BORDER_PX + CAPTION_OFFSET_PX

    draw.text((tx, ty), CAPTION_TEXT, fill=CREAM, font=font)

    # 6️⃣  Save 16‑bit TIFF with the sRGB profile from our temp PNG
    icc = Image.open(tmp_path).info.get("icc_profile")
    save_kwargs = dict(dpi=(DPI, DPI))
    if icc:
        save_kwargs["icc_profile"] = icc
    canvas.save(OUTPUT_FILE, **save_kwargs)
    print(f"✅  Saved {OUTPUT_FILE} ({W_PX}×{H_PX}px @ {DPI} dpi)")


if __name__ == "__main__":
    main()
    subprocess.run(["open", str(OUTPUT_FILE)])  # Automatically open the image on macOS
