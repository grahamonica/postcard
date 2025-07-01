#!/usr/bin/env python3
"""
Make a 4×6-inch (300 dpi) postcard with a cream border and caption,
preserving the original iPhone colour by tone-mapping to sRGB with macOS `sips`.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess, shutil, sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

# ────────── CONFIG ───────────────────────────────────────────────────────────
INPUT_FILE   = Path("boxwork.png")
OUTPUT_FILE  = Path("boxwork_postcard.tif")


DPI          = 300
WIDTH_IN, HT_IN = 4, 6             # inches (portrait)
CREAM        = (245, 245, 220)     # RGB
BORDER_IN    = 0.05                # inches
CAPTION_TEXT = "Wind Cave National Park"

CANDIDATE_FONTS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
]
# ──────────────────────────────────────────────────────────────────────────────


def run_sips_to_srgb(src: Path, dst: Path):
    """Use macOS sips to tone-map & convert *src* into 16-bit sRGB at *dst*."""
    sips_cmd = [
        "sips",
        "--matchTo", "/System/Library/ColorSync/Profiles/sRGB Profile.icc",
        str(src),
        "--out", str(dst),
    ]

    try:
        subprocess.run(sips_cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print("❌  sips failed:\n", e.stderr.decode() or e.stdout.decode(), file=sys.stderr)
        sys.exit(1)


def choose_font(pt_size: int):
    for p in CANDIDATE_FONTS:
        try:
            return ImageFont.truetype(p, pt_size)
        except OSError:
            pass
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, txt: str, font):
    x0, y0, x1, y1 = draw.textbbox((0, 0), txt, font=font)
    return x1 - x0, y1 - y0


def fit_font(draw, txt, max_w, max_h):
    lo, hi = 8, 500
    while lo < hi:
        mid = (lo + hi + 1) // 2
        font = choose_font(mid)
        if all(v <= lim for v, lim in zip(text_size(draw, txt, font), (max_w, max_h))):
            lo = mid
        else:
            hi = mid - 1
    return choose_font(lo)


def largest_crop(img, ratio):
    w, h = img.size
    if w / h > ratio:
        nw = int(h * ratio)
        left = (w - nw) // 2
        return img.crop((left, 0, left + nw, h))
    nh = int(w / ratio)
    top = (h - nh) // 2
    return img.crop((0, top, w, top + nh))


def main():
    if not INPUT_FILE.exists():
        sys.exit(f"❌  {INPUT_FILE} not found")

    # 1) Tone-map & convert to sRGB via sips
    with NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    run_sips_to_srgb(INPUT_FILE, tmp_path)

    # 2) Pillow operations (now safe—image is plain sRGB)
    img = ImageOps.exif_transpose(Image.open(tmp_path))

    # crop   ---------------------------------------------------
    img = largest_crop(img, WIDTH_IN / HT_IN)

    # resize ---------------------------------------------------
    W_PX, H_PX = int(WIDTH_IN * DPI), int(HT_IN * DPI)
    BORDER_PX  = int(BORDER_IN * DPI)
    inner_w, inner_h = W_PX - 2*BORDER_PX, H_PX - 2*BORDER_PX
    img = img.resize((inner_w, inner_h), resample=Image.BOX)

    # border canvas -------------------------------------------
    canvas = Image.new("RGB", (W_PX, H_PX), CREAM)
    canvas.paste(img, (BORDER_PX, BORDER_PX))

    # caption --------------------------------------------------
    draw = ImageDraw.Draw(canvas)
    font = fit_font(draw, CAPTION_TEXT, inner_w, int(0.10 * H_PX))
    tw, th = text_size(draw, CAPTION_TEXT, font)
    x = (W_PX - tw)//2
    y = H_PX - BORDER_PX - th
    draw.text((x, y), CAPTION_TEXT, fill=CREAM, font=font)

    # 3) Save postcard (embed the sRGB ICC profile we already have)
    icc = img.info.get("icc_profile")
    save_kwargs = dict(dpi=(DPI, DPI), optimize=True)
    if icc:
        save_kwargs["icc_profile"] = icc
    canvas.save(OUTPUT_FILE, dpi=(DPI, DPI))

    print(f"✅  Saved {OUTPUT_FILE} ({W_PX}×{H_PX}px @ {DPI} dpi)")

    # 4) Clean up temp file
    try:
        tmp_path.unlink(missing_ok=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
