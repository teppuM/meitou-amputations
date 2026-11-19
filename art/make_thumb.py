"""Builds the Workshop thumbnail in the Execution thumbnail's style: an in-game shot cropped square to 1024, the title in large cream
Georgia Bold and "[ MeitouClient ]" in gold under it, both with a dark outline and drop shadow.
Usage: python make_thumb.py <shot.png> <out.jpg> [crop left top size]"""
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB')
if len(sys.argv) > 5:
    l, t, s = (int(v) for v in sys.argv[3:6])
    im = im.crop((l, t, l + s, t + s))
im = im.resize((1024, 1024), Image.LANCZOS)
im = ImageEnhance.Contrast(ImageEnhance.Brightness(im).enhance(1.3)).enhance(1.08)   # the game's interiors are dark
top = Image.new('L', (1024, 1024), 0)                       # darken the top so the title reads
g = ImageDraw.Draw(top)
for y in range(380):
    g.line([(0, y), (1024, y)], fill=int(150 * (1 - y / 380) ** 1.5))
im = Image.composite(Image.new('RGB', im.size, (0, 0, 0)), im, top)
draw = ImageDraw.Draw(im)


def centred(text, size, y, fill, stroke):
    font = ImageFont.truetype(r'C:\Windows\Fonts\georgiab.ttf', size)
    while draw.textlength(text, font=font) > 970:
        size -= 4; font = ImageFont.truetype(r'C:\Windows\Fonts\georgiab.ttf', size)
    x = (1024 - draw.textlength(text, font=font)) / 2
    for dx, dy in [(5, 6), (3, 4)]:
        draw.text((x + dx, y + dy), text, font=font, fill=(10, 6, 4))
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill=(22, 12, 6))


centred('AMPUTATIONS', 150, 40, (236, 228, 208), 5)
centred('[ MeitouClient ]', 64, 225, (232, 186, 92), 4)
im.save(out, 'JPEG', quality=90)
print(out, Image.open(out).size)
