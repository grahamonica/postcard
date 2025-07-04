import re
from pathlib import Path

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except:
        return None

def is_near_white(rgb, threshold=20):
    if rgb is None:
        return False
    r, g, b = rgb
    return r > 255 - threshold and g > 255 - threshold and b > 255 - threshold

def clean_svg_colors(svg_text):
    # Replace attribute colors
    def replace_attr(match):
        attr = match.group(1)
        value = match.group(2)
        rgb = hex_to_rgb(value)
        if is_near_white(rgb):
            return ''  # remove white-ish
        return f'{attr}="#001f3f"'  # everything else → navy

    svg_text = re.sub(r'(fill|stroke)\s*=\s*["\']#?([0-9a-fA-F]{3,6})["\']', replace_attr, svg_text)

    # Replace inline style colors
    def replace_style(match):
        attr = match.group(1)
        value = match.group(2)
        rgb = hex_to_rgb(value)
        if is_near_white(rgb):
            return ''  # remove white-ish
        return f'{attr}:#001f3f;'  # everything else → navy

    svg_text = re.sub(r'(fill|stroke)\s*:\s*#?([0-9a-fA-F]{3,6})\s*;', replace_style, svg_text)

    return svg_text

def process_file(filepath):
    path = Path(filepath)
    if not path.exists():
        print(f"❌ File not found: {filepath}")
        return

    svg_text = path.read_text(encoding='utf-8')
    cleaned_svg = clean_svg_colors(svg_text)

    if cleaned_svg != svg_text:
        path.write_text(cleaned_svg, encoding='utf-8')
        print(f"✅ Updated: {filepath}")
    else:
        print("⚠️  No changes made. (Colors may already be navy or white was only present.)")

if __name__ == "__main__":
    process_file("mountains.svg")
