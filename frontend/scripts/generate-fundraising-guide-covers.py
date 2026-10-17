"""Generate the exact-text editorial illustrations used by the two free guides.

The graphics are drawn from scratch, with an illustrated board table and strategy
document. The committed PNGs require no extra deployment dependencies.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public/social"
FONT = Path("/usr/share/fonts/truetype/dejavu")
INK, PURPLE, PAPER = "#191d3e", "#4f46d6", "#faf9f6"


def font(size, bold=False):
    return ImageFont.truetype(str(FONT / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)


def person(draw, x, y, color=PURPLE):
    draw.ellipse((x-12, y-21, x+12, y+3), fill=color)
    draw.rounded_rectangle((x-22, y+10, x+22, y+44), radius=12, fill=color)


def document(draw, x, y, width=124, height=170, label="Strategy"):
    draw.rounded_rectangle((x+7, y+8, x+width+7, y+height+8), radius=9, fill="#d6d1e8")
    draw.rounded_rectangle((x, y, x+width, y+height), radius=9, fill="white", outline="#b7b0d8", width=2)
    draw.rounded_rectangle((x+14, y+16, x+width-14, y+21), radius=2, fill=PURPLE)
    draw.text((x+13, y+37), label, font=font(14, True), fill=INK)
    for line, length in enumerate([width-28, width-42, width-30, width-50]):
        yy=y+77+line*18
        draw.rounded_rectangle((x+14, yy, x+length, yy+4), radius=2, fill="#c6c0dc")


for name, lines, subtitle, illustration in [
    ("board-fundraising-three-steps.png", ["Get your board", "raising money", "by your next", "board meeting"], "Create the strategy with your board.", "board"),
    ("fundraising-strategy-three-steps.png", ["Create the right", "fundraising", "strategy for your", "organization"], "Agree on how your organization will raise money.", "strategy"),
]:
    image=Image.new("RGB",(1200,630),PAPER)
    draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,1200,8),fill=PURPLE)
    draw.text((65,62),"THREE STEPS",font=font(16,True),fill=PURPLE)
    for index,line in enumerate(lines):
        draw.text((62,120+index*72),line,font=font(55,True),fill=PURPLE if index>=2 else INK)
    draw.text((65,438),subtitle,font=font(19),fill="#535a70")
    if illustration=="board":
        draw.ellipse((727,111,1140,471),fill="#eeebf8")
        draw.rounded_rectangle((798,191,1074,381),radius=65,fill="#dad5ed",outline="#aaa2d2",width=2)
        person(draw,841,130);person(draw,1015,130,color="#847ae5")
        person(draw,760,251,color="#847ae5");person(draw,1110,251)
        person(draw,841,397);person(draw,1015,397,color="#847ae5")
        document(draw,884,212,107,142,"Our strategy")
    else:
        draw.ellipse((721,109,1151,484),fill="#eeebf8")
        for x,y in [(784,149),(1065,161),(779,344),(1085,366)]:
            draw.line((x,y+20,934,295),fill="#aca2db",width=3)
            draw.ellipse((x-34,y-34,x+34,y+34),fill="#e1dcf2",outline="#b9b0df",width=2)
            person(draw,x,y-13,color="#847ae5")
        document(draw,859,203,164,221,"Funding strategy")
        draw.rounded_rectangle((876,349,1006,402),radius=7,fill=PURPLE)
        draw.text((894,363),"Ideal funders",font=font(14,True),fill="white")
    draw.rectangle((0,527,1200,630),fill=INK)
    draw.text((65,562),"Nonprofit Board Builder",font=font(22,True),fill="white")
    label="With Rooney Akpesiri"
    draw.text((1135-draw.textlength(label,font=font(17)),567),label,font=font(17),fill="#c3bdff")
    OUT.mkdir(parents=True,exist_ok=True)
    image.save(OUT/name,optimize=True)
    print(name)
