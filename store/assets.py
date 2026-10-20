"""Icons and banners of the Odoo Mates WhatsApp apps, in WhatsApp colors.

    python3 store/assets.py

Writes icon.png (600 x 600) of om_whatsapp_base, om_whatsapp_web, om_whatsapp
(Meta) and om_whatsapp_device, and the icons of the extension (src/icons); the
banners and stories are made by stories.py. With module names, only those:

    python3 store/assets.py om_whatsapp
"""
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
EXTENSION = os.path.dirname(HERE)
ODOOAPPS = os.path.join(os.path.dirname(EXTENSION), 'odooapps')
LATO = os.path.expanduser('~/odoo/20.0/odoo/odoo/addons/web/static/fonts/lato')

GREEN = (37, 211, 102)
TEAL = (18, 140, 126)
DARK = (7, 94, 84)
BUBBLE = (220, 248, 198)
CHAT = (236, 229, 221)
TICK = (83, 189, 235)
ODOO = (113, 75, 103)
WHITE = (255, 255, 255)
INK = (17, 27, 33)
MUTED = (102, 119, 129)

S = 4  # drawn larger, then reduced: smooth edges


def font(weight, size):
    name = {'regular': 'Reg', 'bold': 'Bol', 'black': 'Bla'}[weight]
    return ImageFont.truetype(os.path.join(LATO, f'Lato-{name}-webfont.ttf'), size)


def gradient(size, top, bottom):
    """Diagonal gradient, top-left to bottom-right."""
    w, h = size
    down = Image.linear_gradient('L').resize((w, h))
    across = Image.linear_gradient('L').rotate(90).transpose(Image.Transpose.FLIP_LEFT_RIGHT).resize((w, h))
    ramp = ImageChops.add(down, across, scale=2)
    return Image.composite(Image.new('RGB', size, bottom), Image.new('RGB', size, top), ramp)


def rounded_mask(size, radius):
    mask = Image.new('L', size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return mask


# ------------------------------------------------------------
# Glyphs, drawn in a box (x0, y0, x1, y1) at scale S
# ------------------------------------------------------------

def chat_bubble(d, cx, cy, r, width, color):
    """A round bubble with its tail at the bottom left, as chat apps draw it."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=width)
    a = math.radians(125)
    base1 = (cx + (r - width / 2) * math.cos(a + 0.28), cy + (r - width / 2) * math.sin(a + 0.28))
    base2 = (cx + (r - width / 2) * math.cos(a - 0.28), cy + (r - width / 2) * math.sin(a - 0.28))
    tip = (cx - r * 1.08, cy + r * 1.08)
    d.polygon([base1, tip, base2], fill=color)


def send_arrow(d, cx, cy, size, color):
    """The arrow of a send button, pointing right."""
    s = size
    d.polygon([(cx - s * 0.5, cy - s * 0.5), (cx + s * 0.6, cy), (cx - s * 0.5, cy + s * 0.5), (cx - s * 0.28, cy)],
              fill=color)


def badge_lines(d, box, color):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    for i, length in enumerate((0.62, 0.62, 0.4)):
        y = y0 + h * (0.3 + i * 0.2)
        d.rounded_rectangle([x0 + w * 0.19, y - h * 0.05, x0 + w * (0.19 + length), y + h * 0.05], radius=h * 0.05,
                            fill=color)


def badge_browser(d, box, color):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    frame = [x0 + w * 0.18, y0 + h * 0.24, x1 - w * 0.18, y1 - h * 0.24]
    d.rounded_rectangle(frame, radius=h * 0.07, outline=color, width=int(h * 0.075))
    d.rectangle([frame[0], frame[1], frame[2], frame[1] + h * 0.14], fill=color)
    for i in range(3):
        cx = frame[0] + w * (0.09 + i * 0.075)
        cy = frame[1] + h * 0.07
        r = h * 0.024
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ODOO)


def badge_cloud(d, box, color):
    """A cloud: the Cloud API of Meta."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    base = [x0 + w * 0.2, y0 + h * 0.5, x1 - w * 0.2, y0 + h * 0.7]
    d.rounded_rectangle(base, radius=h * 0.1, fill=color)
    for cx, cy, r in ((0.38, 0.5, 0.14), (0.56, 0.42, 0.18), (0.7, 0.54, 0.12)):
        d.ellipse([x0 + w * (cx - r), y0 + h * (cy - r), x0 + w * (cx + r), y0 + h * (cy + r)], fill=color)


def badge_qr(d, box, color):
    """A QR code: linked with a QR code."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cell = w * 0.085
    left, top = x0 + w * 0.26, y0 + h * 0.26
    for cx, cy in ((0, 0), (3.5, 0), (0, 3.5)):
        fx, fy = left + cx * cell, top + cy * cell
        d.rectangle([fx, fy, fx + 2.5 * cell, fy + 2.5 * cell], outline=color, width=int(cell * 0.6))
        d.rectangle([fx + 0.9 * cell, fy + 0.9 * cell, fx + 1.6 * cell, fy + 1.6 * cell], fill=color)
    for cx, cy in ((3.7, 3.7), (4.9, 3.7), (3.7, 4.9), (4.9, 4.9), (4.3, 4.3)):
        fx, fy = left + cx * cell, top + cy * cell
        d.rectangle([fx, fy, fx + 0.7 * cell, fy + 0.7 * cell], fill=color)


# ------------------------------------------------------------
# Icon
# ------------------------------------------------------------

def make_icon(badge=None, size=600, shadow=True):
    big = size * S
    icon = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    margin = 0.2 if shadow else 0.0
    t0, t1 = int(big * margin), int(big * (1 - margin))
    tile = t1 - t0
    radius = int(tile * 0.24)
    if shadow:
        blur = Image.new('RGBA', (big, big), (0, 0, 0, 0))
        ImageDraw.Draw(blur).rounded_rectangle([t0, t0 + big * 0.03, t1, t1 + big * 0.03], radius=radius,
                                               fill=(7, 94, 84, 90))
        icon.alpha_composite(blur.filter(ImageFilter.GaussianBlur(big * 0.035)))
    face = gradient((tile, tile), GREEN, TEAL).convert('RGBA')
    sheen = Image.new('RGBA', (tile, tile), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).ellipse([-tile * 0.5, -tile * 1.05, tile * 1.5, tile * 0.42], fill=(255, 255, 255, 26))
    face.alpha_composite(sheen)
    icon.paste(face, (t0, t0), rounded_mask((tile, tile), radius))

    d = ImageDraw.Draw(icon)
    cx, cy = t0 + tile * 0.5, t0 + tile * 0.47
    r = tile * 0.3
    chat_bubble(d, cx, cy, r, int(tile * 0.062), WHITE)
    send_arrow(d, cx + tile * 0.01, cy, tile * 0.27, WHITE)

    if badge:
        # with a shadow the badge overlaps the corner; full size, it stays inside the tile
        inset, br = (0.04, 0.19) if shadow else (0.21, 0.165)
        bc = (t1 - tile * inset, t1 - tile * inset)
        br = tile * br
        ring = tile * 0.035
        d.ellipse([bc[0] - br - ring, bc[1] - br - ring, bc[0] + br + ring, bc[1] + br + ring], fill=WHITE)
        d.ellipse([bc[0] - br, bc[1] - br, bc[0] + br, bc[1] + br], fill=ODOO)
        badge(d, (bc[0] - br, bc[1] - br, bc[0] + br, bc[1] + br), WHITE)
    return icon.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------

def main():
    badges = {
        'om_whatsapp_base': badge_lines,
        'om_whatsapp_web': badge_browser,
        'om_whatsapp': badge_cloud,
        'om_whatsapp_device': badge_qr,
    }
    wanted = sys.argv[1:] or list(badges) + ['extension']
    for module, badge in badges.items():
        if module not in wanted:
            continue
        target = os.path.join(ODOOAPPS, module, 'static', 'description')
        # full size: the app icon of the home screen of Odoo, as large as the other apps
        make_icon(badge, shadow=False).save(os.path.join(target, 'icon.png'))
        print(module, 'icon.png')
    if 'extension' not in wanted:
        return
    plain = make_icon(None, size=512, shadow=False)
    for size in (16, 32, 48, 128):
        plain.resize((size, size), Image.LANCZOS).save(os.path.join(EXTENSION, 'src', 'icons', f'icon-{size}.png'))
    print('extension icons')


if __name__ == '__main__':
    main()
