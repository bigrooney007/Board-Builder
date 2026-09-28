"""Regenerate the exact-text social cards: python scripts/generate-share-images.py.

Uses Pillow and DejaVu Sans. Generated PNGs are committed, so deployment needs neither.
"""
from pathlib import Path
import json
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "social"
OUT.mkdir(parents=True, exist_ok=True)
FONT_ROOT = Path(os.environ.get("SHARE_CARD_FONT_DIR", "/usr/share/fonts/truetype/dejavu"))


def font(size, bold=False):
    return ImageFont.truetype(str(FONT_ROOT / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)


for page in json.loads((ROOT / "src/content/landingSeo.json").read_text()):
    card = Image.new("RGB", (1200, 630), "#0f172a")
    draw = ImageDraw.Draw(card)
    draw.ellipse((880, -170, 1450, 400), fill="#171e41")
    draw.ellipse((997, -60, 1340, 282), outline="#373078", width=2)
    draw.ellipse((1070, 13, 1267, 210), outline="#4f46a2", width=2)
    draw.rectangle((0, 0, 12, 630), fill="#6366f1")
    draw.rounded_rectangle((72, 58, 88, 74), radius=4, fill="#a5b4fc")
    draw.text((103, 50), "NONPROFIT BOARD BUILDER", font=font(22, True), fill="#f8fafc")
    draw.text((72, 132), page["eyebrow"], font=font(17, True), fill="#a5b4fc")

    size = 66
    while max(draw.textlength(line, font=font(size, True)) for line in page["imageLines"]) > 1056:
        size -= 1
    y = 184
    for line in page["imageLines"]:
        draw.text((68, y), line, font=font(size, True), fill="#ffffff")
        y += size + 12

    sub_y = max(y + 22, 417)
    sub_font = font(23)
    words, lines, current = page["imageSub"].split(), [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if draw.textlength(candidate, font=sub_font) > 1056:
            lines.append(current)
            current = word
        else:
            current = candidate
    lines.append(current)
    for line in lines:
        draw.text((72, sub_y), line, font=sub_font, fill="#cbd5e1")
        sub_y += 32
    if sub_y > 515:
        raise ValueError(f"Subtitle overlaps footer: {page['path']}")

    draw.line((72, 526, 1128, 526), fill="#334155", width=1)
    draw.text((72, 559), "nonprofitboardbuilder.com", font=font(21, True), fill="#ffffff")
    signature = "With Rooney Akpesiri"
    draw.text((1128 - draw.textlength(signature, font=font(18)), 563), signature, font=font(18), fill="#a5b4fc")
    card.save(OUT / page["image"], optimize=True)
    print(page["image"])
