from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess, sys
from PIL import (Image, ImageDraw, ImageFont, ImageOps)

# ────────── CONFIG ───────────────────────────────────────────────────────────
INPUT_FILE        = Path("boxwork.png")
OUTPUT_FILE       = Path("boxwork.tif")

# postcard geometry
DPI               = 300
WIDTH_IN, HT_IN   = 4, 6              # inches (portrait)
BORDER_IN         = 0.1              # inches
CREAM             = (195, 197, 176)   # border colour

# caption
CAPTION_LINES     = ["Wind Cave", "National Park"]
CAPTION_POS       = "bottom"          # "bottom" or "top"
CAPTION_ALIGN     = "left"            # "center" | "left" | "right"
CAPTION_OFFSET_PX = -75              # +ve moves text up (bottom) / down (top)
CAPTION_FONT_SIZE = 300             # None = auto fit
CAPTION_LINE_OFFSETS = [100, 100]        # horizontal offsets for each line

# font – set explicit path to Ironick NF (adjust if installed elsewhere)
FONT_PATH         = "/Users/monicagraham/Downloads/Fonts/IronickNF.otf"

# gradient shadow (drawn only inside the photo area, not over the border)
ADD_SHADOW          = True            # toggle shadow on/off
SHADOW_COLOR        = (24, 18, 12)       # base colour of shadow
SHADOW_OPACITY      = 1          # 0‑1 darkest opacity at bottom edge
SHADOW_HEIGHT_FRAC  = 0.55            # fraction of inner‑photo height

# caption drop shadow
TEXT_SHADOW         = True
TEXT_SHADOW_COLOR   = (0, 0, 0)
TEXT_SHADOW_OPACITY = 0.5
TEXT_SHADOW_OFFSET  = (3, 3)
TEXT_FILL_COLOR     = CREAM

# ─────────────────────────────────────────────────────────────────────────────


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
            pass
    return ImageFont.load_default()


def text_dims(draw, text, font):
    x0, y0, x1, y1 = draw.textbbox((0, 0), text, font=font)
    return x1 - x0, y1 - y0


def fit_font(draw, lines, max_w, max_h):
    lo, hi = 6, 600
    while lo < hi:
        mid  = (lo + hi + 1) // 2
        font = pick_font(mid)
        line_heights = [text_dims(draw, line, font)[1] for line in lines]
        line_widths  = [text_dims(draw, line, font)[0] for line in lines]
        total_h = sum(line_heights) + (len(lines) - 1) * int(0.15 * mid)
        if max(line_widths) <= max_w and total_h <= max_h:
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


def add_shadow_gradient(base: Image.Image, border_px: int):
    if not ADD_SHADOW or SHADOW_OPACITY <= 0 or SHADOW_HEIGHT_FRAC <= 0:
        return base

    w, h      = base.size
    inner_w   = w - 2 * border_px
    inner_h   = h - 2 * border_px
    grad_h    = int(inner_h * SHADOW_HEIGHT_FRAC)

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


def main():
    if not INPUT_FILE.exists():
        sys.exit("input image not found")

    with NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    run_sips_to_srgb(INPUT_FILE, tmp_path)

    img = ImageOps.exif_transpose(Image.open(tmp_path))
    img = largest_crop(img, WIDTH_IN / HT_IN)

    inner_width_in = WIDTH_IN - 2 * BORDER_IN
    inner_height_in = HT_IN - 2 * BORDER_IN

    inner_w_px, inner_h_px = img.size
    dpi_x = inner_w_px / inner_width_in
    dpi_y = inner_h_px / inner_height_in
    DPI = int((dpi_x + dpi_y) / 2)

    border_px = int(BORDER_IN * DPI)
    W_PX = inner_w_px + 2 * border_px
    H_PX = inner_h_px + 2 * border_px

    canvas = Image.new("RGB", (W_PX, H_PX), CREAM)
    canvas.paste(img, (border_px, border_px))
    canvas = add_shadow_gradient(canvas, border_px)

    draw = ImageDraw.Draw(canvas)
    font = pick_font(CAPTION_FONT_SIZE) if CAPTION_FONT_SIZE else fit_font(draw, CAPTION_LINES, inner_w_px, int(0.12 * H_PX))

    line_height = font.getbbox("Hg")[3]
    total_text_height = int(len(CAPTION_LINES) * line_height + (len(CAPTION_LINES) - 1) * 0.15 * font.size)

    if CAPTION_POS == "bottom":
        ty = H_PX - border_px - total_text_height + CAPTION_OFFSET_PX
    else:
        ty = border_px + CAPTION_OFFSET_PX

    for i, line in enumerate(CAPTION_LINES):
        tw, th = text_dims(draw, line, font)
        if CAPTION_ALIGN == "center":
            tx = (W_PX - tw) // 2 + CAPTION_LINE_OFFSETS[i]
        elif CAPTION_ALIGN == "right":
            tx = W_PX - border_px - tw + CAPTION_LINE_OFFSETS[i]
        else:
            tx = border_px + CAPTION_LINE_OFFSETS[i]

        if TEXT_SHADOW:
            shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(shadow)
            shadow_color = TEXT_SHADOW_COLOR + (int(255 * TEXT_SHADOW_OPACITY),)
            sx, sy = tx + TEXT_SHADOW_OFFSET[0], ty + TEXT_SHADOW_OFFSET[1]
            d.text((sx, sy), line, font=font, fill=shadow_color)
            canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB")
            draw = ImageDraw.Draw(canvas)

        draw.text((tx, ty), line, fill=TEXT_FILL_COLOR, font=font)
        ty += int(line_height + 0.15 * font.size)

    icc = Image.open(tmp_path).info.get("icc_profile")
    save_kwargs = dict(dpi=(DPI, DPI))
    if icc:
        save_kwargs["icc_profile"] = icc
    canvas.save(OUTPUT_FILE, **save_kwargs)
    print(f"Saved {OUTPUT_FILE} ({W_PX}×{H_PX}px @ {DPI} dpi)")
    subprocess.run(["open", str(OUTPUT_FILE)])

if __name__ == "__main__":
    main()