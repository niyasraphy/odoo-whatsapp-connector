"""Stories of the Odoo Mates WhatsApp apps: what each module does, as a short
film for the top of its store page (story.gif, 1280 x 720), and its banner
(banner.gif, 1152 x 648) as a short loop of the same moment. Drawn, in the
colors of assets.py: no real data, small files.

    python3 store/stories.py                     # every module
    python3 store/stories.py om_whatsapp_web     # only those
"""
import copy
import functools
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import assets
from assets import BUBBLE, CHAT, DARK, GREEN, INK, MUTED, ODOO, TEAL, TICK, WHITE

K = 2  # drawn twice as large, then reduced: smooth edges
NOTO_EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
PAPER = (247, 251, 248)
SOFT = (232, 246, 238)
LINE = (222, 226, 230)
LINK = (1, 126, 132)
GREY_BG = (245, 247, 249)
LIGHT_TEXT = (73, 80, 87)


# ------------------------------------------------------------
# Drawing, in the coordinates of the final image
# ------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def lato(weight, size):
    return assets.font(weight, int(size * K))


@functools.lru_cache(maxsize=None)
def emoji_image(char, size):
    big = ImageFont.truetype(NOTO_EMOJI, 109)
    im = Image.new('RGBA', (180, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), char, font=big, embedded_color=True)
    im = im.crop(im.getbbox())
    side = int(size * K)
    return im.resize((side, int(side * im.height / im.width)), Image.LANCZOS)


@functools.lru_cache(maxsize=None)
def module_icon(badge_name, size):
    badge = getattr(assets, badge_name) if badge_name else None
    return assets.make_icon(badge).resize((int(size * K), int(size * K)), Image.LANCZOS)


class Canvas:

    def __init__(self, size, bg=PAPER):
        self.size = size
        self.img = Image.new('RGB', (size[0] * K, size[1] * K), bg)
        self.d = ImageDraw.Draw(self.img, 'RGBA')
        self.targets = {}

    @staticmethod
    def k(box):
        return [v * K for v in box]

    def rect(self, box, fill=None, r=0, outline=None, width=1):
        if r:
            self.d.rounded_rectangle(self.k(box), radius=r * K, fill=fill, outline=outline, width=width * K)
        else:
            self.d.rectangle(self.k(box), fill=fill, outline=outline, width=width * K)

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse(self.k(box), fill=fill, outline=outline, width=width * K)

    def line(self, points, fill, width=1):
        self.d.line([(x * K, y * K) for x, y in points], fill=fill, width=int(width * K), joint='curve')

    def polygon(self, points, fill, outline=None):
        self.d.polygon([(x * K, y * K) for x, y in points], fill=fill, outline=outline)

    def text(self, xy, text, size, weight='regular', fill=INK, anchor='la'):
        self.d.text((xy[0] * K, xy[1] * K), text, font=lato(weight, size), fill=fill, anchor=anchor)

    def length(self, text, size, weight='regular'):
        return self.d.textlength(text, font=lato(weight, size)) / K

    def emoji(self, center, char, size):
        im = emoji_image(char, size)
        self.img.paste(im, (int(center[0] * K - im.width / 2), int(center[1] * K - im.height / 2)), im)

    def paste(self, im, xy):
        self.img.paste(im, (int(xy[0] * K), int(xy[1] * K)), im if im.mode == 'RGBA' else None)

    def shadow(self, box, r=14, color=DARK, alpha=46, blur=14, dy=8):
        """A soft shadow under ``box``, blurred in its own region only."""
        pad = blur * 3
        x0, y0, x1, y1 = box
        w, h = int((x1 - x0 + 2 * pad) * K), int((y1 - y0 + 2 * pad) * K)
        mask = Image.new('L', (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([pad * K, pad * K, w - pad * K, h - pad * K], radius=r * K, fill=alpha)
        mask = mask.filter(ImageFilter.GaussianBlur(blur * K / 2))
        self.img.paste(Image.new('RGB', (w, h), color), (int((x0 - pad) * K), int((y0 - pad + dy) * K)), mask)

    def wrap(self, text, size, width, weight='regular'):
        lines, line = [], ''
        for word in text.split():
            candidate = f'{line} {word}'.strip()
            if self.length(candidate, size, weight) > width and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        return lines + [line] if line else lines

    def final(self):
        return self.img.resize(self.size, Image.LANCZOS)


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)


# ------------------------------------------------------------
# Pieces
# ------------------------------------------------------------

def ticks(c, x, y, level, z=1.0):
    """1: sent (one grey tick), 2: delivered (two grey), 3: read (two blue)."""
    if not level:
        return
    color = TICK if level >= 3 else (140, 150, 156)
    marks = (0,) if level == 1 else (0, 5 * z)
    for dx in marks:
        c.line([(x + dx, y + 5 * z), (x + dx + 3.5 * z, y + 8.5 * z), (x + dx + 10 * z, y)], color, 1.6 * z)


def clock(c, x, y, z=1.0):
    c.ellipse([x, y, x + 10 * z, y + 10 * z], outline=(140, 150, 156), width=1)
    c.line([(x + 5 * z, y + 2.5 * z), (x + 5 * z, y + 5 * z), (x + 7.5 * z, y + 6 * z)], (140, 150, 156), 1)


def pdf_card(c, box, name, z=1.0, fill=(205, 236, 182)):
    x0, y0, x1, y1 = box
    c.rect(box, fill=fill, r=7 * z)
    c.rect([x0 + 9 * z, y0 + 8 * z, x0 + 37 * z, y1 - 8 * z], fill=(229, 57, 53), r=4 * z)
    c.text((x0 + 23 * z, (y0 + y1) / 2), 'PDF', 9 * z, 'black', WHITE, anchor='mm')
    c.text((x0 + 46 * z, y0 + 9 * z), name, 13 * z, 'bold', INK)
    c.text((x0 + 46 * z, y0 + 27 * z), '1 page · PDF', 11 * z, 'regular', MUTED)


def bubble_layout(c, m, maxw, z):
    """(width, height) of a message bubble."""
    size = 14.5 * z
    lines = c.wrap(m.get('text', ''), size, maxw - 26 * z) if m.get('text') else []
    width = max([c.length(line, size) for line in lines] + [0]) + 26 * z
    height = 10 * z + len(lines) * 19 * z + 18 * z
    if m.get('pdf'):
        width = max(width, min(maxw, 236 * z))
        height += 50 * z
    width = max(width, 96 * z)
    return width, height, lines


def messages(c, area, msgs, z=1.0, in_fill=WHITE, out_fill=BUBBLE, gap=8, left=False):
    """The messages, the last at the bottom; older ones go out at the top;
    all on the left with ``left`` (the chatter). Returns the boxes of the
    bubbles drawn, in the order of ``msgs``."""
    x0, y0, x1, y1 = area
    maxw = (x1 - x0) * 0.8
    y = y1 - 6 * z
    boxes = [None] * len(msgs)
    for i in range(len(msgs) - 1, -1, -1):
        m = msgs[i]
        width, height, lines = bubble_layout(c, m, maxw, z)
        if m.get('reaction'):
            y -= 16 * z
        top = y - height
        if top < y0:
            break
        out = m['side'] == 'out'
        bx0 = x1 - 8 * z - width if out and not left else x0 + 8 * z
        bx1 = bx0 + width
        c.rect([bx0, top, bx1, y], fill=out_fill if out else in_fill, r=10 * z)
        ty = top + 8 * z
        if m.get('pdf'):
            pdf_card(c, [bx0 + 5 * z, top + 5 * z, bx1 - 5 * z, top + 49 * z], m['pdf'], z,
                     fill=(205, 236, 182) if out else (240, 242, 245))
            ty += 48 * z
        for k_, line in enumerate(lines):
            c.text((bx0 + 13 * z, ty + k_ * 19 * z), line, 14.5 * z, 'regular', INK)
        has_ticks = out and m.get('ticks', 0) != -1
        c.text((bx1 - (40 if has_ticks else 12) * z, y - 6 * z), m.get('time', '10:42'), 10.5 * z, 'regular', MUTED,
               anchor='rb')
        if out:
            if m.get('ticks') == 0:
                clock(c, bx1 - 22 * z, y - 16 * z, z)
            elif m.get('ticks', 0) > 0:
                ticks(c, bx1 - 28 * z, y - 15 * z, m.get('ticks', 0), z)
        if m.get('reaction'):
            rx = bx0 + 10 * z if not out or left else bx1 - 40 * z
            c.rect([rx, y - 7 * z, rx + 34 * z, y + 18 * z], fill=WHITE, r=12.5 * z, outline=LINE)
            c.emoji((rx + 17 * z, y + 5.5 * z), m['reaction'], 16 * z)
        boxes[i] = (bx0, top, bx1, y)
        y = top - gap * z
    return boxes


def cursor(c, xy, click=False):
    if not xy:
        return
    x, y = xy
    if click:
        c.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(37, 211, 102, 70))
    arrow = [(0, 0), (0, 21), (5, 16.5), (9, 25), (12.5, 23.5), (8.5, 15), (15, 15)]
    c.polygon([(x + px + 1.5, y + py + 2) for px, py in arrow], fill=(0, 0, 0, 60))
    c.polygon([(x + px, y + py) for px, py in arrow], fill=INK)
    inner = [(1.6, 4), (1.6, 17), (5.2, 13.6), (9.6, 22.4), (10.6, 22), (6.4, 13.2), (11.4, 13.2)]
    c.polygon([(x + px, y + py) for px, py in inner], fill=WHITE)


def toast(c, x, y, text, width=None):
    width = width or c.length(text, 15, 'bold') + 90
    c.shadow([x, y, x + width, y + 54], r=10, alpha=40, blur=10, dy=4)
    c.rect([x, y, x + width, y + 54], fill=WHITE, r=10, outline=(214, 236, 222))
    c.rect([x, y + 6, x + 5, y + 48], fill=GREEN)
    c.ellipse([x + 20, y + 14, x + 46, y + 40], fill=GREEN)
    c.line([(x + 26.5, y + 27), (x + 31, y + 32), (x + 40, y + 21)], WHITE, 2.6)
    c.text((x + 60, y + 27), text, 15, 'bold', INK, anchor='lm')


def button(c, x, y, label, kind='secondary', name=None, icon=None, h=32, size=13.5):
    width = c.length(label, size, 'bold') + 2 * size + (22 if icon else 0)
    fills = {'primary': (ODOO, WHITE, None), 'secondary': ((233, 236, 239), INK, None),
             'green': (GREEN, WHITE, None), 'light': (WHITE, INK, LINE)}
    fill, color, outline = fills[kind]
    c.rect([x, y, x + width, y + h], fill=fill, r=6, outline=outline)
    tx = x + 14
    if icon == 'whatsapp':
        c.ellipse([x + 11, y + h / 2 - 8, x + 27, y + h / 2 + 8], fill=GREEN)
        assets_bubble(c, x + 19, y + h / 2, 4.4)
        tx += 22
    c.text((tx, y + h / 2), label, size, 'bold', color, anchor='lm')
    if name:
        c.targets[name] = (x + width / 2, y + h / 2)
    return x + width


def assets_bubble(c, cx, cy, r):
    """The bubble with a send arrow of the icon, small and white."""
    c.ellipse([cx - r, cy - r, cx + r, cy + r], outline=WHITE, width=1)
    c.polygon([(cx - r * 0.45, cy - r * 0.45), (cx + r * 0.6, cy), (cx - r * 0.45, cy + r * 0.45)], fill=WHITE)


def avatar(c, box, letter, fill=(178, 223, 219), color=DARK):
    x0, y0, x1, y1 = box
    c.ellipse(box, fill=fill)
    c.text(((x0 + x1) / 2, (y0 + y1) / 2 + 1), letter, (y1 - y0) * 0.45, 'black', color, anchor='mm')


def chips(c, x, y, items, size=16, first_filled=True):
    for i, label in enumerate(items):
        width = c.length(label, size, 'bold') + 34
        filled = first_filled and i == 0
        c.rect([x, y, x + width, y + 40], fill=GREEN if filled else SOFT, r=20)
        c.text((x + 17, y + 20), label, size, 'bold', WHITE if filled else DARK, anchor='lm')
        x += width + 10
    return x


# ------------------------------------------------------------
# The phone of the customer, and the screens of Odoo
# ------------------------------------------------------------

def phone(c, box, title, msgs, typing='', subtitle='online', scan=None):
    x0, y0, x1, y1 = box
    c.shadow(box, r=38, alpha=55, blur=16, dy=12)
    c.rect(box, fill=(32, 40, 44), r=38)
    sx0, sy0, sx1, sy1 = x0 + 9, y0 + 9, x1 - 9, y1 - 9
    if scan is not None:
        return phone_camera(c, (sx0, sy0, sx1, sy1), scan)
    c.rect([sx0, sy0, sx1, sy1], fill=CHAT, r=30)
    for i in range(13):
        for j in range(7):
            px, py = sx0 + 22 + j * 40 + (i % 2) * 20, sy0 + 104 + i * 36
            if px < sx1 - 10 and py < sy1 - 70:
                c.ellipse([px, py, px + 3, py + 3], fill=(225, 216, 205))
    c.rect([sx0, sy0, sx1, sy0 + 88], fill=DARK, r=30)
    c.rect([sx0, sy0 + 50, sx1, sy0 + 88], fill=DARK)
    c.rect([(sx0 + sx1) / 2 - 38, sy0 + 8, (sx0 + sx1) / 2 + 38, sy0 + 26], fill=(32, 40, 44), r=9)
    c.text((sx0 + 26, sy0 + 17), '10:42', 11.5, 'bold', WHITE, anchor='lm')
    avatar(c, [sx0 + 14, sy0 + 40, sx0 + 52, sy0 + 78], title[0])
    c.text((sx0 + 62, sy0 + 44), title, 16, 'bold', WHITE)
    c.text((sx0 + 62, sy0 + 64), subtitle, 11.5, 'regular', (178, 223, 219))
    boxes = messages(c, [sx0 + 4, sy0 + 96, sx1 - 4, sy1 - 62], msgs, z=0.92)
    c.rect([sx0 + 10, sy1 - 52, sx1 - 54, sy1 - 12], fill=WHITE, r=20)
    if typing:
        shown = typing
        while c.length(shown, 13.5) > sx1 - sx0 - 96 and len(shown) > 4:
            shown = shown[1:]
        c.text((sx0 + 26, sy1 - 32), shown, 13.5, 'regular', INK, anchor='lm')
        cx = sx0 + 27 + c.length(shown, 13.5)
        c.line([(cx, sy1 - 41), (cx, sy1 - 23)], TEAL, 1.5)
    else:
        c.text((sx0 + 26, sy1 - 32), 'Message', 13.5, 'regular', MUTED, anchor='lm')
    c.ellipse([sx1 - 48, sy1 - 52, sx1 - 8, sy1 - 12], fill=TEAL)
    assets.send_arrow(c.d, (sx1 - 27) * K, (sy1 - 32) * K, 15 * K, WHITE)
    return boxes


def phone_camera(c, screen, scan):
    """The phone scanning a QR code: Linked devices of WhatsApp."""
    sx0, sy0, sx1, sy1 = screen
    c.rect(screen, fill=(18, 24, 27), r=30)
    c.text(((sx0 + sx1) / 2, sy0 + 50), 'Link a device', 16, 'bold', WHITE, anchor='mm')
    c.text(((sx0 + sx1) / 2, sy0 + 74), 'Point your phone at the screen', 11.5, 'regular', (170, 180, 185), anchor='mm')
    fx0, fy0 = sx0 + 34, sy0 + 130
    fx1, fy1 = sx1 - 34, fy0 + (sx1 - sx0 - 68)
    qr(c, (fx0 + 26, fy0 + 26, fx1 - 26, fy1 - 26), fg=(200, 205, 208), bg=(18, 24, 27))
    for (cx, cy, dx, dy) in ((fx0, fy0, 1, 1), (fx1, fy0, -1, 1), (fx0, fy1, 1, -1), (fx1, fy1, -1, -1)):
        c.line([(cx, cy + dy * 30), (cx, cy), (cx + dx * 30, cy)], GREEN, 4)
    if scan < 1:
        y = fy0 + (fy1 - fy0) * scan
        c.rect([fx0 + 6, y - 1.5, fx1 - 6, y + 1.5], fill=(37, 211, 102, 200))
    else:
        c.ellipse([(sx0 + sx1) / 2 - 30, fy1 + 40, (sx0 + sx1) / 2 + 30, fy1 + 100], fill=GREEN)
        c.line([((sx0 + sx1) / 2 - 13, fy1 + 70), ((sx0 + sx1) / 2 - 3, fy1 + 80), ((sx0 + sx1) / 2 + 15, fy1 + 60)],
               WHITE, 4)


def qr(c, box, fg=INK, bg=WHITE, seed=7):
    x0, y0, x1, y1 = box
    n = 25
    cell = (x1 - x0) / n
    rnd = random.Random(seed)
    c.rect(box, fill=bg)
    finders = [(0, 0), (n - 7, 0), (0, n - 7)]

    def in_finder(i, j):
        return any(fx <= i < fx + 8 and fy <= j < fy + 8 for fx, fy in finders)
    for i in range(n):
        for j in range(n):
            if not in_finder(i, j) and rnd.random() < 0.48:
                c.rect([x0 + i * cell, y0 + j * cell, x0 + (i + 1) * cell, y0 + (j + 1) * cell], fill=fg)
    for fx, fy in finders:
        c.rect([x0 + fx * cell, y0 + fy * cell, x0 + (fx + 7) * cell, y0 + (fy + 7) * cell], fill=fg)
        c.rect([x0 + (fx + 1) * cell, y0 + (fy + 1) * cell, x0 + (fx + 6) * cell, y0 + (fy + 6) * cell], fill=bg)
        c.rect([x0 + (fx + 2) * cell, y0 + (fy + 2) * cell, x0 + (fx + 5) * cell, y0 + (fy + 5) * cell], fill=fg)


def odoo_window(c, box, app, menus, chat_badge=0, clock_text=None):
    x0, y0, x1, y1 = box
    c.shadow(box, r=12, alpha=40, blur=16, dy=10)
    c.rect(box, fill=WHITE, r=12)
    c.rect([x0, y0, x1, y0 + 42], fill=ODOO, r=12)
    c.rect([x0, y0 + 20, x1, y0 + 42], fill=ODOO)
    for i in range(3):
        for j in range(3):
            c.rect([x0 + 18 + i * 6, y0 + 14 + j * 6, x0 + 21.5 + i * 6, y0 + 17.5 + j * 6], fill=WHITE)
    c.text((x0 + 48, y0 + 21), app, 15, 'bold', WHITE, anchor='lm')
    x = x0 + 58 + c.length(app, 15, 'bold')
    for menu in menus:
        c.text((x, y0 + 21), menu, 13.5, 'regular', (235, 225, 232), anchor='lm')
        x += c.length(menu, 13.5) + 22
    # right: the chat icon with its counter, the user
    rx = x1 - 26
    avatar(c, [rx - 13, y0 + 8, rx + 13, y0 + 34], 'M', fill=(246, 201, 105), color=(120, 70, 0))
    bx = rx - 46
    c.rect([bx - 9, y0 + 13, bx + 9, y0 + 27], outline=WHITE, r=4, width=1)
    c.polygon([(bx - 4, y0 + 27), (bx - 6, y0 + 32), (bx + 1, y0 + 27)], fill=WHITE)
    if chat_badge:
        c.ellipse([bx + 3, y0 + 5, bx + 19, y0 + 21], fill=GREEN)
        c.text((bx + 11, y0 + 13), str(chat_badge), 10, 'black', WHITE, anchor='mm')
    if clock_text:
        cx = bx - 110
        c.rect([cx - 4, y0 + 9, cx + 80, y0 + 33], fill=(90, 58, 82), r=12)
        c.ellipse([cx + 6, y0 + 14, cx + 20, y0 + 28], fill=(250, 220, 120))
        c.ellipse([cx + 11, y0 + 11, cx + 25, y0 + 25], fill=(90, 58, 82))
        c.text((cx + 30, y0 + 21), clock_text, 13, 'bold', WHITE, anchor='lm')
    return [x0, y0 + 42, x1, y1]


DOCUMENTS = {
    'S00042': {
        'list': 'Quotations', 'title': 'S00042', 'steps': ['Quotation', 'Quotation Sent', 'Sales Order'],
        'fields': [('Customer', 'Wood Corner'), ('Quotation Date', '10/20/2026'),
                   ('Expiration', '11/19/2026'), ('Payment Terms', '30 Days')],
        'lines': [('Oak Dining Table', '1.00', '1,250.00'), ('Oak Chair', '4.00', '720.00')],
        'total': '$ 1,970.00',
    },
    'S00051': {
        'list': 'Sales Orders', 'title': 'S00051', 'steps': ['Quotation', 'Quotation Sent', 'Sales Order'],
        'fields': [('Customer', 'Wood Corner'), ('Order Date', '10/20/2026'),
                   ('Source', 'Website'), ('Payment Terms', 'Immediate')],
        'lines': [('Oak Bookcase', '1.00', '640.00'), ('Delivery', '1.00', '40.00')],
        'total': '$ 680.00',
    },
    'INV/2026/00042': {
        'list': 'Invoices', 'title': 'INV/2026/00042', 'steps': ['Draft', 'Posted'],
        'fields': [('Customer', 'Wood Corner'), ('Invoice Date', '10/20/2026'),
                   ('Due Date', '11/19/2026'), ('Payment Terms', '30 Days')],
        'lines': [('Oak Dining Table', '1.00', '1,250.00'), ('Oak Chair', '4.00', '720.00')],
        'total': '$ 1,970.00',
    },
}


def form(c, area, doc, status, buttons, chatter=None):
    """A form of Odoo: breadcrumb, buttons, status bar, sheet, and the
    chatter on the right when given (a list of entries, the newest first)."""
    x0, y0, x1, y1 = area
    spec = DOCUMENTS[doc]
    c.rect([x0, y0, x1, y1], fill=GREY_BG)
    c.text((x0 + 20, y0 + 22), spec['list'], 15, 'regular', LINK, anchor='lm')
    c.text((x0 + 26 + c.length(spec['list'], 15), y0 + 22), f"/ {spec['title']}", 15, 'regular', INK, anchor='lm')
    chatter_w = 330 if chatter is not None else 0
    bx = x0 + 20
    for label, kind, name, icon in buttons:
        bx = button(c, bx, y0 + 44, label, kind, name, icon) + 6
    # status bar: the first steps go when there is no room, as in Odoo
    sx = x1 - chatter_w - 20
    steps = list(spec['steps'])
    while len(steps) > 1 and sum(c.length(st, 12.5, 'bold') + 30 for st in steps) > sx - bx - 10:
        steps.pop(0)
    for step in reversed(steps):
        width = c.length(step, 12.5, 'bold') + 26
        active = step == status
        c.rect([sx - width, y0 + 44, sx, y0 + 76], fill=(232, 222, 229) if active else WHITE,
               outline=None if active else LINE, r=6)
        c.text((sx - width / 2, y0 + 60), step, 12.5, 'bold', ODOO if active else MUTED, anchor='mm')
        sx -= width + 4
    # sheet
    sx0, sy0, sx1, sy1 = x0 + 20, y0 + 90, x1 - chatter_w - 20, y1 - 14
    c.rect([sx0, sy0, sx1, sy1], fill=WHITE, outline=LINE, r=6)
    c.text((sx0 + 24, sy0 + 22), spec['title'], 26, 'bold', INK)
    col = (sx1 - sx0 - 48) / 2
    for i, (label, value) in enumerate(spec['fields']):
        fx = sx0 + 24 + (i % 2) * col
        fy = sy0 + 72 + (i // 2) * 32
        c.text((fx, fy), label, 13, 'bold', LIGHT_TEXT)
        c.text((fx + 120, fy), value, 13, 'regular', LINK if label == 'Customer' else INK)
    ty = sy0 + 150
    c.line([(sx0 + 24, ty + 26), (sx1 - 24, ty + 26)], LINE, 1)
    for label, xr in (('Product', 0), ('Quantity', 0.55), ('Amount', 0.82)):
        c.text((sx0 + 24 + (sx1 - sx0 - 48) * xr, ty + 6), label, 12.5, 'bold', LIGHT_TEXT)
    for k_, (product, qty, amount) in enumerate(spec['lines']):
        ry = ty + 38 + k_ * 32
        c.text((sx0 + 24, ry), product, 13, 'regular', INK)
        c.text((sx0 + 24 + (sx1 - sx0 - 48) * 0.55, ry), qty, 13, 'regular', INK)
        c.text((sx0 + 24 + (sx1 - sx0 - 48) * 0.82, ry), amount, 13, 'regular', INK)
        c.line([(sx0 + 24, ry + 24), (sx1 - 24, ry + 24)], (238, 240, 242), 1)
    c.text((sx1 - 24, ty + 38 + len(spec['lines']) * 32 + 14), f"Total:  {spec['total']}", 15, 'bold', INK,
           anchor='ra')
    if chatter is not None:
        chatter_panel(c, [x1 - chatter_w, y0, x1, y1], chatter)


def chatter_panel(c, area, entries):
    x0, y0, x1, y1 = area
    c.rect([x0, y0, x1, y1], fill=WHITE)
    c.line([(x0, y0), (x0, y1)], LINE, 1)
    bx = x0 + 14
    for label, kind in (('Send message', 'primary'), ('Log note', 'secondary'), ('WhatsApp', 'secondary')):
        bx = button(c, bx, y0 + 14, label, kind, h=28, size=12, icon='whatsapp' if label == 'WhatsApp' else None) + 5
    y = y0 + 58
    c.text((x0 + 14, y), 'Today', 11.5, 'bold', MUTED)
    y += 22
    for entry in entries:
        if y > y1 - 40:
            break
        avatar(c, [x0 + 14, y, x0 + 46, y + 32], entry['author'][0],
               fill=(178, 223, 219) if entry.get('customer') else (246, 201, 105),
               color=DARK if entry.get('customer') else (120, 70, 0))
        c.text((x0 + 56, y + 1), entry['author'], 13, 'bold', INK)
        c.text((x0 + 62 + c.length(entry['author'], 13, 'bold'), y + 2), entry.get('time', '10:42'), 11.5,
               'regular', MUTED)
        if entry.get('whatsapp'):
            c.ellipse([x1 - 34, y + 1, x1 - 18, y + 17], fill=GREEN)
            assets_bubble(c, x1 - 26, y + 9, 4.4)
        msg = {'side': 'in' if entry.get('customer') else 'out', 'text': entry.get('text'), 'pdf': entry.get('pdf'),
               'ticks': entry.get('ticks'), 'reaction': entry.get('reaction'), 'time': entry.get('time', '10:42')}
        width, height, _lines = bubble_layout(c, msg, x1 - x0 - 70, 0.9)
        extra = 16 * 0.9 if msg['reaction'] else 0
        if msg['side'] == 'out' and msg['ticks'] is None:
            msg['ticks'] = -1  # a note: no ticks
        messages(c, [x0 + 48, y + 20, x1 - 8, y + 26 + height + extra], [msg], z=0.9, in_fill=(240, 242, 245),
                 out_fill=(233, 247, 238), left=True)
        y += 32 + height + extra + 14


def chat_window(c, box, name, msgs, draft='', focused=False, banner=None, picker=None):
    x0, y0, x1, y1 = box
    c.shadow(box, r=10, alpha=50, blur=14, dy=6)
    c.rect(box, fill=WHITE, r=10)
    c.rect([x0, y0, x1, y0 + 46], fill=WHITE, r=10)
    c.line([(x0, y0 + 46), (x1, y0 + 46)], LINE, 1)
    avatar(c, [x0 + 12, y0 + 9, x0 + 40, y0 + 37], name[0])
    c.ellipse([x0 + 30, y0 + 25, x0 + 44, y0 + 39], fill=GREEN, outline=WHITE, width=1)
    c.text((x0 + 52, y0 + 23), name, 14.5, 'bold', INK, anchor='lm')
    c.text((x1 - 40, y0 + 23), '–', 16, 'bold', MUTED, anchor='mm')
    c.text((x1 - 18, y0 + 23), '×', 18, 'bold', MUTED, anchor='mm')
    body_top = y0 + 47
    c.rect([x0, body_top, x1, y1 - 58], fill=GREY_BG)
    if banner:
        c.rect([x0 + 10, body_top + 8, x1 - 10, body_top + 34], fill=(232, 246, 238), r=6)
        c.text(((x0 + x1) / 2, body_top + 21), banner, 11.5, 'bold', DARK, anchor='mm')
        body_top += 34
    boxes = messages(c, [x0 + 2, body_top + 6, x1 - 2, y1 - 64], msgs, z=0.86, in_fill=WHITE, out_fill=BUBBLE)
    for i, b in enumerate(boxes):
        if b:
            c.targets[f'chat_msg_{i}'] = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            c.targets[f'chat_box_{i}'] = b
    c.rect([x0 + 10, y1 - 48, x1 - 50, y1 - 12], fill=WHITE, outline=TEAL if focused else LINE, r=8,
           width=2 if focused else 1)
    c.targets['chat_input'] = (x0 + 80, y1 - 30)
    if draft:
        c.text((x0 + 22, y1 - 30), draft, 13.5, 'regular', INK, anchor='lm')
        cx = x0 + 23 + c.length(draft, 13.5)
        c.line([(cx, y1 - 39), (cx, y1 - 21)], TEAL, 1.5)
    else:
        c.text((x0 + 22, y1 - 30), f'Message {name}...', 13.5, 'regular', MUTED, anchor='lm')
    c.ellipse([x1 - 44, y1 - 48, x1 - 8, y1 - 12], fill=TEAL)
    assets.send_arrow(c.d, (x1 - 25) * K, (y1 - 30) * K, 13 * K, WHITE)
    if picker is not None:
        b = boxes[picker]
        if b:
            px0, py1 = b[0], b[1] - 4
            c.shadow([px0, py1 - 38, px0 + 150, py1], r=19, alpha=40, blur=8, dy=3)
            c.rect([px0, py1 - 38, px0 + 150, py1], fill=WHITE, r=19, outline=LINE)
            for i, char in enumerate(('👍', '❤️', '😂', '🙏')):
                cx = px0 + 22 + i * 35
                c.emoji((cx, py1 - 19), char, 21)
                c.targets[f'emoji_{i}'] = (cx, py1 - 19)


def discuss(c, area, chats, selected, msgs, header_extra=None, draft=''):
    """Discuss: the WhatsApp chats in the sidebar, the selected one open."""
    x0, y0, x1, y1 = area
    c.rect([x0, y0, x0 + 250, y1], fill=(250, 250, 251))
    c.line([(x0 + 250, y0), (x0 + 250, y1)], LINE, 1)
    y = y0 + 18
    for label in ('Inbox', 'Starred', 'History'):
        c.text((x0 + 22, y + 10), label, 14, 'regular', INK, anchor='lm')
        y += 32
    y += 10
    c.ellipse([x0 + 20, y + 3, x0 + 34, y + 17], fill=GREEN)
    assets_bubble(c, x0 + 27, y + 10, 4)
    c.text((x0 + 42, y + 10), 'WHATSAPP', 12, 'black', MUTED, anchor='lm')
    y += 30
    for i, chat in enumerate(chats):
        active = i == selected
        if active:
            c.rect([x0 + 8, y - 4, x0 + 242, y + 36], fill=(232, 222, 229), r=6)
        avatar(c, [x0 + 18, y, x0 + 50, y + 32], chat['name'][0] if chat['name'][0] != '+' else '#',
               fill=chat.get('color', (178, 223, 219)))
        c.text((x0 + 60, y + 16), chat['name'], 13.5, 'bold' if chat.get('unread') else 'regular', INK, anchor='lm')
        if chat.get('unread'):
            c.ellipse([x0 + 214, y + 6, x0 + 234, y + 26], fill=GREEN)
            c.text((x0 + 224, y + 16), str(chat['unread']), 11, 'black', WHITE, anchor='mm')
        c.targets[f'chat_row_{i}'] = (x0 + 120, y + 16)
        y += 46
    # the conversation
    cx0 = x0 + 251
    c.rect([cx0, y0, x1, y0 + 60], fill=WHITE)
    c.line([(cx0, y0 + 60), (x1, y0 + 60)], LINE, 1)
    chat = chats[selected]
    avatar(c, [cx0 + 18, y0 + 12, cx0 + 54, y0 + 48], chat['name'][0] if chat['name'][0] != '+' else '#',
           fill=chat.get('color', (178, 223, 219)))
    c.text((cx0 + 66, y0 + 18), chat['name'], 16, 'bold', INK)
    c.text((cx0 + 66, y0 + 40), chat.get('detail', 'WhatsApp · Sales Team'), 12, 'regular', MUTED)
    hx = x1 - 20
    for label, kind, name in reversed(header_extra or []):
        width = c.length(label, 13.5, 'bold') + 28
        button(c, hx - width, y0 + 14, label, kind, name)
        hx -= width + 8
    c.rect([cx0, y0 + 61, x1, y1 - 64], fill=GREY_BG)
    messages(c, [cx0 + 20, y0 + 70, x1 - 20, y1 - 70], msgs, z=1.0, in_fill=WHITE, out_fill=BUBBLE)
    c.rect([cx0, y1 - 63, x1, y1], fill=WHITE)
    c.rect([cx0 + 20, y1 - 50, x1 - 70, y1 - 14], fill=WHITE, outline=LINE, r=8)
    c.text((cx0 + 34, y1 - 32), draft or f"Message {chat['name']}...", 13.5, 'regular', INK if draft else MUTED,
           anchor='lm')
    c.ellipse([x1 - 58, y1 - 50, x1 - 22, y1 - 14], fill=TEAL)
    assets.send_arrow(c.d, (x1 - 39) * K, (y1 - 32) * K, 13 * K, WHITE)


def list_view(c, area, title, rows, note=None, source_label='Source'):
    """A list of orders, with the WhatsApp status of each."""
    x0, y0, x1, y1 = area
    c.rect([x0, y0, x1, y1], fill=GREY_BG)
    c.text((x0 + 20, y0 + 22), title, 17, 'bold', INK, anchor='lm')
    c.rect([x1 - 300, y0 + 8, x1 - 20, y0 + 38], fill=WHITE, outline=LINE, r=6)
    c.text((x1 - 288, y0 + 23), 'Search...', 13, 'regular', MUTED, anchor='lm')
    tx0, ty0, tx1 = x0 + 20, y0 + 52, x1 - 20
    c.rect([tx0, ty0, tx1, ty0 + 36 + max(len(rows), 1) * 44], fill=WHITE, outline=LINE, r=6)
    cols = (('Number', 0.02), ('Customer', 0.17), (source_label, 0.42), ('Status', 0.58), ('WhatsApp', 0.8))
    for label, xr in cols:
        c.text((tx0 + (tx1 - tx0) * xr, ty0 + 18), label, 12.5, 'bold', LIGHT_TEXT, anchor='lm')
    c.line([(tx0, ty0 + 36), (tx1, ty0 + 36)], LINE, 1)
    for i, row in enumerate(rows):
        ry = ty0 + 36 + i * 44
        if i:
            c.line([(tx0 + 10, ry), (tx1 - 10, ry)], (238, 240, 242), 1)
        mid = ry + 22
        c.text((tx0 + (tx1 - tx0) * 0.02, mid), row['number'], 13.5, 'bold', INK, anchor='lm')
        c.text((tx0 + (tx1 - tx0) * (0.21 if len(row['number']) > 8 else 0.17), mid), row['customer'], 13.5,
               'regular', INK, anchor='lm')
        c.text((tx0 + (tx1 - tx0) * 0.42, mid), row.get('source', 'Website'), 13.5, 'regular', MUTED, anchor='lm')
        badge = row.get('status', 'Sales Order')
        bw = c.length(badge, 12, 'bold') + 20
        bx = tx0 + (tx1 - tx0) * 0.58
        c.rect([bx, mid - 11, bx + bw, mid + 11], fill=(214, 240, 222), r=11)
        c.text((bx + bw / 2, mid), badge, 12, 'bold', DARK, anchor='mm')
        wx = tx0 + (tx1 - tx0) * 0.8
        state = row.get('whatsapp')
        if state is not None:
            labels = {0: 'Queued', 1: 'Sent', 2: 'Delivered', 3: 'Read'}
            if state == 0:
                clock(c, wx, mid - 5, 1.1)
            else:
                ticks(c, wx, mid - 5, state, 1.1)
            c.text((wx + 22, mid), labels[state], 12.5, 'regular', MUTED, anchor='lm')
    if note:
        ny = y1 - 76
        c.rect([x0 + 20, ny, x1 - 20, ny + 58], fill=WHITE, outline=(190, 230, 205), r=8)
        c.rect([x0 + 20, ny, x0 + 26, ny + 58], fill=GREEN)
        c.text((x0 + 42, ny + 19), note[0], 14, 'bold', DARK, anchor='lm')
        c.text((x0 + 42, ny + 40), note[1], 12.5, 'regular', MUTED, anchor='lm')
        if len(note) > 2:
            nw = c.length(note[2], 12, 'bold') + 24
            c.rect([x1 - 36 - nw, ny + 17, x1 - 36, ny + 41], fill=GREEN, r=12)
            c.text((x1 - 36 - nw / 2, ny + 29), note[2], 12, 'bold', WHITE, anchor='mm')


def dialog(c, area, title, rows, body, attachment, send_name='dialog_send'):
    """The Send WhatsApp composer of Odoo, over the dimmed page."""
    x0, y0, x1, y1 = area
    c.rect([x0, y0, x1, y1], fill=(0, 0, 0, 90))
    dw, dh = 560, 440
    dx0, dy0 = (x0 + x1) / 2 - dw / 2, y0 + 50
    c.shadow([dx0, dy0, dx0 + dw, dy0 + dh], r=10, alpha=70, blur=18, dy=10)
    c.rect([dx0, dy0, dx0 + dw, dy0 + dh], fill=WHITE, r=10)
    c.text((dx0 + 24, dy0 + 28), title, 18, 'bold', INK, anchor='lm')
    c.text((dx0 + dw - 24, dy0 + 28), '×', 20, 'bold', MUTED, anchor='mm')
    c.line([(dx0, dy0 + 56), (dx0 + dw, dy0 + 56)], LINE, 1)
    y = dy0 + 76
    for label, value in rows:
        c.text((dx0 + 24, y + 10), label, 13.5, 'bold', LIGHT_TEXT, anchor='lm')
        c.text((dx0 + 150, y + 10), value, 13.5, 'regular', INK, anchor='lm')
        c.line([(dx0 + 150, y + 24), (dx0 + dw - 24, y + 24)], LINE, 1)
        y += 40
    c.rect([dx0 + 24, y, dx0 + dw - 24, y + 96], fill=WHITE, outline=LINE, r=6)
    for k_, line in enumerate(c.wrap(body, 14, dw - 80)):
        c.text((dx0 + 38, y + 14 + k_ * 21), line, 14, 'regular', INK)
    y += 112
    pdf_card(c, [dx0 + 24, y, dx0 + 260, y + 44], attachment, 1.0, fill=(240, 242, 245))
    by = dy0 + dh - 54
    c.line([(dx0, by - 12), (dx0 + dw, by - 12)], LINE, 1)
    nx = button(c, dx0 + 24, by, 'Send', 'primary', send_name)
    button(c, nx + 8, by, 'Discard', 'secondary')


# ------------------------------------------------------------
# Films: a list of states, each drawn into a frame
# ------------------------------------------------------------

class Film:

    def __init__(self, render, start):
        self.render = render
        self.state = copy.deepcopy(start)
        self.frames = []

    def hold(self, ms, **changes):
        self.state.update(changes)
        self.frames.append((copy.deepcopy(self.state), ms))

    def type(self, key, text, ms=650, steps=9):
        for i in range(1, steps + 1):
            self.state[key] = text[:round(len(text) * i / steps)]
            self.frames.append((copy.deepcopy(self.state), ms // steps))

    def target(self, name):
        return self.render(self.state).targets[name]

    def move(self, to, steps=7, ms=420):
        if isinstance(to, str):
            to = self.target(to)
        start = self.state.get('cursor') or (to[0] - 160, to[1] + 120)
        for i in range(1, steps + 1):
            t = ease(i / steps)
            self.state['cursor'] = (start[0] + (to[0] - start[0]) * t, start[1] + (to[1] - start[1]) * t)
            self.frames.append((copy.deepcopy(self.state), ms // steps))

    def click(self, ms=160):
        self.state['click'] = True
        self.frames.append((copy.deepcopy(self.state), ms))
        self.state['click'] = False

    def slide(self, key, steps=5, ms=300):
        for i in range(1, steps + 1):
            self.state[key] = ease(i / steps)
            self.frames.append((copy.deepcopy(self.state), ms // steps))

    def save(self, path):
        merged = []
        for state, ms in self.frames:
            if merged and merged[-1][0] == state:
                merged[-1][1] += ms
            else:
                merged.append([state, ms])
        images = [self.render(state).final() for state, _ms in merged]
        durations = [max(ms, 40) for _state, ms in merged]
        save_gif(path, images, durations)
        return len(images)


def save_gif(path, images, durations):
    """One palette for every frame, from a montage of some of them."""
    picks = images[:: max(1, len(images) // 8)][:8] + [images[-1]]
    w, h = images[0].size
    montage = Image.new('RGB', (w, h * (len(picks) + 1)), PAPER)
    for i, im in enumerate(picks):
        montage.paste(im, (0, h * i))
    # small but vivid: the red of the PDF, the ticks, the emojis keep their colors
    swatch_y = h * len(picks)
    for i, color in enumerate(((229, 57, 53), TICK, GREEN, TEAL, DARK, ODOO, (246, 201, 105), BUBBLE)):
        montage.paste(color, (i * (w // 8), swatch_y, (i + 1) * (w // 8), swatch_y + h // 3))
    for i, char in enumerate(('👍', '❤️', '😂', '🙏')):
        im = emoji_image(char, 110)
        montage.paste(im, (i * (w // 4) + 20, swatch_y + h // 3 + 20), im)
    palette = montage.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    frames = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in images]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=False,
                   disposal=1)


# ------------------------------------------------------------
# The stage of a story
# ------------------------------------------------------------

SW, SH = 1280, 720


def stage(state, spec):
    c = Canvas((SW, SH))
    c.ellipse([-300, 420, 380, 1100], fill=SOFT)
    c.ellipse([980, -320, 1560, 220], fill=SOFT)
    c.rect([0, 0, SW, 6], fill=DARK)
    c.rect([0, SH - 6, SW * 0.62, SH], fill=DARK)
    c.rect([SW * 0.62, SH - 6, SW, SH], fill=GREEN)
    if state.get('end'):
        end_card(c, spec)
        return c, False
    step, text = state['caption']
    c.ellipse([40, 24, 80, 64], fill=GREEN)
    c.text((60, 44), str(step), 20, 'black', WHITE, anchor='mm')
    c.text((94, 31), text, 24, 'black', DARK, anchor='lm')
    if state.get('sub'):
        c.text((95, 59), state['sub'], 14.5, 'regular', MUTED, anchor='lm')
    icon = module_icon(spec['badge'], 40)
    c.paste(icon, (SW - 250, 22))
    c.text((SW - 202, 34), spec['short'], 16, 'black', DARK, anchor='lm')
    c.text((SW - 202, 54), 'by Odoo Mates', 12, 'bold', MUTED, anchor='lm')
    return c, True


def end_card(c, spec):
    icon = module_icon(spec['badge'], 150)
    c.paste(icon, (SW / 2 - 75, 120))
    c.text((SW / 2, 312), spec['end_title'], 46, 'black', DARK, anchor='mm')
    c.text((SW / 2, 362), spec['end_sub'], 20, 'regular', MUTED, anchor='mm')
    total = sum(c.length(item, 16, 'bold') + 34 for item in spec['items']) + 10 * (len(spec['items']) - 1)
    chips(c, SW / 2 - total / 2, 404, spec['items'])
    c.text((SW / 2, 500), 'ODOO MATES  ·  ODOO 20 COMMUNITY & ENTERPRISE', 14, 'bold', TEAL, anchor='mm')


# ------------------------------------------------------------
# WhatsApp Web: a customer writes, Odoo answers, the deal closes
# ------------------------------------------------------------

WEB = {
    'badge': 'badge_browser', 'short': 'WhatsApp Web',
    'end_title': 'WhatsApp Web in Odoo 20', 'end_sub': 'Chat with your customers without leaving Odoo',
    'items': ['Free', 'No API', 'Replies & reactions', 'Chrome & Firefox'],
}

WEB_BUTTONS_DRAFT = [('Send by Email', 'secondary', None, None), ('WhatsApp', 'secondary', 'whatsapp', 'whatsapp'),
                     ('Confirm', 'primary', 'confirm', None), ('Cancel', 'secondary', None, None)]
WEB_BUTTONS_DONE = [('Create Invoice', 'primary', None, None), ('WhatsApp', 'secondary', 'whatsapp', 'whatsapp'),
                    ('Cancel', 'secondary', None, None)]


def render_web(state):
    c, playing = stage(state, WEB)
    if not playing:
        return c
    phone(c, [40, 96, 340, 700], 'YourCompany', state['phone'], state.get('typing', ''), 'business account')
    area = odoo_window(c, [380, 96, 1240, 700], 'Sales', ['Orders', 'To Invoice', 'Products', 'Reporting'],
                       chat_badge=state.get('badge', 0))
    done = state['status'] == 'Sales Order'
    form(c, area, 'S00042', state['status'], WEB_BUTTONS_DONE if done else WEB_BUTTONS_DRAFT)
    if state.get('chat', 0):
        top = 700 - 400 * state['chat']
        chat_window(c, [880, top, 1220, top + 400], 'Wood Corner', state['window'], state.get('draft', ''),
                    state.get('focus', False), picker=state.get('picker'))
    if state.get('toast'):
        toast(c, 400, 628, state['toast'])
    cursor(c, state.get('cursor'), state.get('click'))
    return c


def film_web():
    f = Film(render_web, {'caption': (1, 'A customer writes to you on WhatsApp'), 'phone': [], 'window': [],
                          'status': 'Quotation'})
    question = 'Hi! Is the oak table still available?'
    f.hold(900)
    f.type('typing', question, ms=900, steps=10)
    f.hold(300, typing='', phone=[{'side': 'out', 'text': question, 'ticks': 1}])
    f.hold(500, phone=[{'side': 'out', 'text': question, 'ticks': 2}])
    f.hold(200, caption=(2, 'It pops up in Odoo, in a chat window'), badge=1)
    f.state['window'] = [{'side': 'in', 'text': question}]
    f.slide('chat', steps=6, ms=360)
    f.hold(700, badge=0)
    f.hold(1100, phone=[{'side': 'out', 'text': question, 'ticks': 3}])
    answer = 'Yes, it is! I can deliver it on Friday.'
    f.hold(300, caption=(3, 'Answer from Odoo, as you would on WhatsApp'))
    f.move('chat_input')
    f.click()
    f.hold(150, focus=True)
    f.type('draft', answer, ms=900, steps=10)
    f.hold(250, draft='', window=f.state['window'] + [{'side': 'out', 'text': answer, 'ticks': 1}])
    f.hold(350, phone=f.state['phone'] + [{'side': 'in', 'text': answer}])
    f.state['window'][-1]['ticks'] = 3
    f.hold(1200)
    reply = "Perfect, I'll take it!"
    f.hold(200, caption=(4, 'React to their message'), focus=False)
    f.type('typing', reply, ms=650, steps=7)
    f.hold(300, typing='', phone=f.state['phone'] + [{'side': 'out', 'text': reply, 'ticks': 3}])
    f.hold(700, window=f.state['window'] + [{'side': 'in', 'text': reply}])
    f.move(f.target('chat_msg_2'))
    f.hold(500, picker=2)
    f.move('emoji_0', steps=5, ms=300)
    f.click()
    f.state['window'][2]['reaction'] = '👍'
    f.hold(600, picker=None)
    f.state['phone'][2]['reaction'] = '👍'
    f.hold(1400)
    f.hold(200, caption=(5, 'Close the deal: confirm the order'),
           sub='An automation rule sends the order, with its PDF')
    f.move('confirm', steps=8, ms=520)
    f.click()
    f.hold(300, status='Sales Order', toast='WhatsApp sent to Wood Corner.')
    f.move((700, 300), steps=4, ms=240)
    order = {'text': 'Your order S00042 is confirmed. Thank you!', 'pdf': 'Order S00042.pdf'}
    f.hold(400, phone=f.state['phone'] + [dict(order, side='in')],
           window=f.state['window'] + [dict(order, side='out', ticks=2)])
    f.hold(900)
    f.state['window'][-1]['ticks'] = 3
    f.hold(2200, toast=None)
    f.hold(3200, end=True)
    return f


# ------------------------------------------------------------
# Base: every chat in Discuss, a contact in one click, a template from a document
# ------------------------------------------------------------

BASE = {
    'badge': 'badge_lines', 'short': 'WhatsApp',
    'end_title': 'WhatsApp for Odoo 20', 'end_sub': 'Templates, conversations and a log on every document',
    'items': ['Click to Chat', 'WhatsApp Web', 'Meta Cloud API', 'WhatsApp QR'],
}

BASE_CHATS = [
    {'name': 'Wood Corner', 'detail': '+1 555 010 4422 · Quotation S00042'},
    {'name': 'Gemini Furniture', 'unread': 1, 'color': (205, 220, 250), 'detail': '+1 555 019 7788'},
    {'name': 'Deco Addict', 'color': (250, 214, 205), 'detail': '+1 555 016 3300'},
    {'name': '+32 470 55 55 55', 'unread': 1, 'color': (225, 225, 230), 'detail': 'Unknown number · WhatsApp name: Lumber Inc'},
]
BASE_TALKS = {
    0: [{'side': 'in', 'text': 'Hello! Do you have the oak table in stock?', 'time': '09:12'},
        {'side': 'out', 'text': 'Yes! I am sending you the quotation now.', 'ticks': 3, 'time': '09:14'},
        {'side': 'in', 'text': 'Great, thank you!', 'time': '09:15'}],
    1: [{'side': 'in', 'text': 'Can you deliver on Saturday morning?', 'time': '10:31'}],
    3: [{'side': 'in', 'text': 'Hi, I saw your shop online. Do you sell standing desks?', 'time': '10:40'}],
}


def render_base(state):
    c, playing = stage(state, BASE)
    if not playing:
        return c
    if state['view'] == 'discuss':
        area = odoo_window(c, [40, 96, 1240, 700], 'Discuss', [])
        chats = state['chats']
        selected = state['selected']
        extra = None
        if selected == 3 and not state.get('created'):
            extra = [('Create Contact', 'green', 'create_contact')]
        elif selected == 0:
            extra = [('Quotation S00042', 'light', None)]
        discuss(c, area, chats, selected, BASE_TALKS[selected], header_extra=extra)
    else:
        area = odoo_window(c, [40, 96, 1240, 700], 'Sales', ['Orders', 'To Invoice', 'Products', 'Reporting'])
        form(c, area, 'S00042', 'Quotation', WEB_BUTTONS_DRAFT, chatter=state['chatter'])
        if state.get('dialog'):
            dialog(c, area, 'Send WhatsApp', [('Account', 'Sales Team (WhatsApp Web)'), ('Template', 'Sales Quote'),
                                              ('Recipient', 'Wood Corner, +1 555 010 4422')],
                   'Hello Wood Corner, here is your quotation S00042 of $ 1,970.00. It is valid for 30 days.',
                   'S00042.pdf')
    if state.get('toast'):
        toast(c, 860, 150, state['toast'])
    cursor(c, state.get('cursor'), state.get('click'))
    return c


def film_base():
    chats = copy.deepcopy(BASE_CHATS)
    f = Film(render_base, {'caption': (1, 'Every WhatsApp chat of the team, in Discuss'),
                           'sub': 'Sent and received with WhatsApp Web, the Meta Cloud API or WhatsApp QR',
                           'view': 'discuss', 'chats': chats, 'selected': 0})
    f.hold(1800)
    f.move('chat_row_1')
    f.click()
    f.state['chats'][1]['unread'] = 0
    f.hold(1500, selected=1)
    f.hold(200, caption=(2, 'A new number? Make the contact in one click'), sub=None)
    f.move('chat_row_3')
    f.click()
    f.state['chats'][3]['unread'] = 0
    f.hold(1300, selected=3)
    f.move('create_contact')
    f.click()
    f.state['chats'][3].update(name='Lumber Inc', color=(255, 230, 180), detail='+32 470 55 55 55 · Contact created')
    f.hold(1600, created=True, toast='Lumber Inc is now a contact.')
    f.hold(200, toast=None, caption=(3, 'Send from any document, with a template and its PDF'), view='form',
           chatter=[{'author': 'Mitchell Admin', 'text': 'Quotation created', 'time': '09:02'}], cursor=None)
    f.hold(700)
    f.move('whatsapp')
    f.click()
    f.hold(1900, dialog=True)
    f.move('dialog_send')
    f.click()
    sent = {'author': 'Mitchell Admin', 'whatsapp': True, 'time': '10:44', 'ticks': 1,
            'text': 'Hello Wood Corner, here is your quotation S00042 of $ 1,970.00.', 'pdf': 'S00042.pdf'}
    f.hold(500, dialog=False, chatter=[sent] + f.state['chatter'],
           caption=(4, 'Every message on the document, with its ticks'))
    f.state['chatter'][0]['ticks'] = 2
    f.hold(600)
    f.state['chatter'][0]['ticks'] = 3
    f.hold(900)
    reply = {'author': 'Wood Corner', 'customer': True, 'whatsapp': True, 'time': '10:47',
             'text': "Thanks! Looks good, I'll confirm tomorrow."}
    f.hold(2600, chatter=[reply] + f.state['chatter'], cursor=None)
    f.hold(3200, end=True)
    return f


# ------------------------------------------------------------
# Meta: orders day and night, sent from the server, replies through the webhook
# ------------------------------------------------------------

META = {
    'badge': 'badge_cloud', 'short': 'WhatsApp Cloud API',
    'end_title': 'WhatsApp Cloud API in Odoo 20', 'end_sub': 'The official API of Meta, from the server',
    'items': ['Official API', 'Automation', 'Approved templates', 'Two-way chat'],
}

ORDERS = [('S00051', 'Wood Corner'), ('S00052', 'Gemini Furniture'), ('S00053', 'Deco Addict'),
          ('S00054', 'Lumber Inc'), ('S00055', 'Ready Mat')]
TEMPLATE_TEXT = 'Hello Wood Corner, your order S00051 is confirmed. Thank you!'


def render_server(state, spec):
    c, playing = stage(state, spec)
    if not playing:
        return c
    phone(c, [940, 96, 1240, 700], 'YourCompany', state['phone'], state.get('typing', ''), 'business account',
          scan=state.get('scan'))
    view = state['view']
    app, menus = ('Sales', ['Orders', 'To Invoice', 'Products', 'Reporting'])
    if view == 'account':
        app, menus = ('WhatsApp', ['Messages', 'Templates', 'Configuration'])
    if view in ('invoice', 'invoices'):
        app, menus = ('Invoicing', ['Customers', 'Vendors', 'Reporting'])
    area = odoo_window(c, [40, 96, 900, 700], app, menus, clock_text=state.get('night'))
    if view == 'list':
        list_view(c, area, 'Sales Orders', state['rows'], note=state.get('note'))
    elif view == 'invoices':
        list_view(c, area, 'Invoices', state['rows'], note=state.get('note'), source_label='Due Date')
    elif view == 'account':
        account_form(c, area, state)
    else:
        doc = 'INV/2026/00042' if view == 'invoice' else 'S00051'
        status = 'Posted' if view == 'invoice' else 'Sales Order'
        buttons = [('Register Payment' if view == 'invoice' else 'Create Invoice', 'primary', None, None),
                   ('WhatsApp', 'secondary', 'whatsapp', 'whatsapp')]
        form(c, area, doc, status, buttons, chatter=state['chatter'])
        if state.get('chat', 0):
            top = 700 - 400 * state['chat']
            chat_window(c, [540, top, 880, top + 400], 'Wood Corner', state['window'], state.get('draft', ''),
                        state.get('focus', False), banner=state.get('banner'))
    if state.get('toast'):
        toast(c, 470, 150, state['toast'])
    cursor(c, state.get('cursor'), state.get('click'))
    return c


def account_form(c, area, state):
    x0, y0, x1, y1 = area
    c.rect([x0, y0, x1, y1], fill=GREY_BG)
    c.text((x0 + 20, y0 + 22), 'Accounts', 15, 'regular', LINK, anchor='lm')
    c.text((x0 + 26 + c.length('Accounts', 15), y0 + 22), '/ Shop', 15, 'regular', INK, anchor='lm')
    sx0, sy0, sx1, sy1 = x0 + 20, y0 + 48, x1 - 20, y1 - 14
    c.rect([sx0, sy0, sx1, sy1], fill=WHITE, outline=LINE, r=6)
    c.text((sx0 + 24, sy0 + 22), 'Shop', 26, 'bold', INK)
    linked = state.get('linked')
    badge = 'Linked' if linked else 'Not linked'
    bw = c.length(badge, 12.5, 'bold') + 22
    c.rect([sx1 - 24 - bw, sy0 + 26, sx1 - 24, sy0 + 50], fill=(214, 240, 222) if linked else (240, 242, 245), r=12)
    c.text((sx1 - 24 - bw / 2, sy0 + 38), badge, 12.5, 'bold', DARK if linked else MUTED, anchor='mm')
    fields = [('Provider', 'WhatsApp QR (Linked Device)'), ('Number', '+1 555 010 0001' if linked else ''),
              ('Pause between messages', '2 - 6 seconds'), ('Messages a day', '200')]
    for i, (label, value) in enumerate(fields):
        fy = sy0 + 80 + i * 34
        c.text((sx0 + 24, fy), label, 13, 'bold', LIGHT_TEXT)
        c.text((sx0 + 220, fy), value, 13, 'regular', INK)
    # the window with the QR code
    qx0, qy0 = sx0 + 60, sy0 + 230
    qx1, qy1 = sx1 - 60, sy1 - 20
    c.shadow([qx0, qy0, qx1, qy1], r=10, alpha=50, blur=14)
    c.rect([qx0, qy0, qx1, qy1], fill=WHITE, r=10, outline=LINE)
    side = qy1 - qy0 - 40
    if linked:
        c.ellipse([qx0 + 30, qy0 + 30, qx0 + 30 + side * 0.6, qy0 + 30 + side * 0.6], fill=GREEN)
        mx, my, r = qx0 + 30 + side * 0.3, qy0 + 30 + side * 0.3, side * 0.3
        c.line([(mx - r * 0.45, my), (mx - r * 0.1, my + r * 0.35), (mx + r * 0.5, my - r * 0.35)], WHITE, 6)
        tx = qx0 + 50 + side * 0.6
        c.text((tx, qy0 + 60), 'WhatsApp is linked', 20, 'black', DARK)
        c.text((tx, qy0 + 92), '+1 555 010 0001 · on the server', 14, 'regular', MUTED)
        c.text((tx, qy0 + 116), 'Odoo now sends and receives by itself.', 14, 'regular', MUTED)
    else:
        qr(c, (qx0 + 20, qy0 + 20, qx0 + 20 + side, qy0 + 20 + side))
        tx = qx0 + 44 + side
        c.text((tx, qy0 + 34), 'Link WhatsApp', 20, 'black', DARK)
        for k_, line in enumerate(['1. Open WhatsApp on your phone', '2. Settings > Linked devices',
                                   '3. Link a device, and scan this code']):
            c.text((tx, qy0 + 72 + k_ * 26), line, 14, 'regular', INK)


def film_meta():
    rows = [{'number': n, 'customer': who} for n, who in ORDERS]
    f = Film(lambda s: render_server(s, META),
             {'caption': (1, 'Orders come in, day and night'),
              'sub': 'Confirmed on the website, by a payment, by an import: no one at the screen',
              'view': 'list', 'rows': [], 'phone': [], 'night': '02:14'})
    for i in range(len(rows)):
        f.hold(330 if i < len(rows) - 1 else 900, rows=rows[:i + 1])
    f.hold(200, caption=(2, 'Each customer gets a WhatsApp, from the server'),
           sub='An automation rule sends a template approved by Meta, with the PDF of the order',
           note=('Automation rule: when an order is confirmed, Send WhatsApp', 'Template: Order Confirmation',
                 'Approved by Meta'))
    for row in f.state['rows']:
        row['whatsapp'] = 0
    f.hold(700)
    for level in (1, 2):
        for row in f.state['rows']:
            row['whatsapp'] = level
            f.hold(140)
    f.hold(200, phone=[{'side': 'in', 'text': TEMPLATE_TEXT, 'pdf': 'Order S00051.pdf', 'time': '02:14'}])
    for row in f.state['rows'][:3]:
        row['whatsapp'] = 3
        f.hold(260)
    f.hold(1300)
    f.hold(200, caption=(3, 'Replies and reactions come back'), sub='Through the webhook of Meta, onto the order')
    f.state['phone'][0]['reaction'] = '👍'
    f.hold(600)
    question = 'Thanks! When will it arrive?'
    f.type('typing', question, ms=750, steps=8)
    f.hold(300, typing='', phone=f.state['phone'] + [{'side': 'out', 'text': question, 'ticks': 2, 'time': '08:05'}])
    sent = {'author': 'Mitchell Admin', 'whatsapp': True, 'time': '02:14', 'ticks': 3, 'text': TEMPLATE_TEXT,
            'pdf': 'Order S00051.pdf'}
    f.hold(700, view='order', night=None, note=None, chatter=[sent])
    f.state['chatter'][0]['reaction'] = '👍'
    f.hold(700)
    reply = {'author': 'Wood Corner', 'customer': True, 'whatsapp': True, 'time': '08:05', 'text': question}
    f.hold(1400, chatter=[reply] + f.state['chatter'])
    f.state['phone'][-1]['ticks'] = 3
    f.hold(200, caption=(4, 'Answer in free text, within 24 hours'),
           sub='Meta takes free text for 24 hours after the last message of the customer')
    f.state['window'] = [{'side': 'out', 'text': TEMPLATE_TEXT, 'pdf': 'Order S00051.pdf', 'ticks': 3,
                          'time': '02:14'}, {'side': 'in', 'text': question, 'time': '08:05'}]
    f.state['banner'] = 'Free text until tomorrow 08:05'
    f.slide('chat', steps=6, ms=360)
    f.move('chat_input')
    f.click()
    answer = 'It ships on Monday, with a tracking link.'
    f.hold(150, focus=True)
    f.type('draft', answer, ms=900, steps=10)
    f.hold(300, draft='', window=f.state['window'] + [{'side': 'out', 'text': answer, 'ticks': 1, 'time': '08:07'}])
    f.hold(500, phone=f.state['phone'] + [{'side': 'in', 'text': answer, 'time': '08:07'}])
    f.state['window'][-1]['ticks'] = 3
    f.hold(2400, focus=False, cursor=None)
    f.hold(3200, end=True)
    return f


# ------------------------------------------------------------
# WhatsApp QR: scan once, then the server sends and receives
# ------------------------------------------------------------

DEVICE = {
    'badge': 'badge_qr', 'short': 'WhatsApp QR',
    'end_title': 'WhatsApp QR in Odoo 20', 'end_sub': 'Scan once, then Odoo sends and receives from the server',
    'items': ['Scan & go', 'From the server', 'Automation', 'Two-way chat'],
}
INVOICE_TEXT = 'Hello Wood Corner, your invoice INV/2026/00042 is attached. Thank you!'


def film_device():
    f = Film(lambda s: render_server(s, DEVICE),
             {'caption': (1, 'Link your WhatsApp with a QR code, once'),
              'sub': 'As WhatsApp on a computer: Settings > Linked devices on your phone',
              'view': 'account', 'phone': [], 'scan': 0.0})
    f.hold(900)
    for i in range(1, 9):
        f.hold(110, scan=i / 8 if i < 8 else 0.98)
    f.hold(300, scan=1.0)
    f.hold(1800, linked=True)
    rows = [{'number': f'INV/2026/000{42 + i}', 'customer': who, 'source': '11/19/2026', 'status': 'Posted'}
            for i, (_n, who) in enumerate(ORDERS[:4])]
    f.hold(200, caption=(2, 'Odoo sends from the server, no browser open'),
           sub='Automation rules and scheduled actions, a pause between messages, a daily limit',
           view='invoices', rows=rows, scan=None,
           note=('Sent one at a time, as a person would', 'A pause of 2 to 6 seconds, 200 messages a day', 'Safe pace'))
    for row in f.state['rows']:
        row['whatsapp'] = 0
    f.hold(600)
    for i, row in enumerate(f.state['rows']):
        row['whatsapp'] = 2
        if i == 0:
            f.state['phone'] = [{'side': 'in', 'text': INVOICE_TEXT, 'pdf': 'INV-2026-00042.pdf'}]
        f.hold(600)
    f.state['rows'][0]['whatsapp'] = 3
    f.hold(1200)
    f.hold(200, caption=(3, 'Replies come back to the document'), sub='And to the conversation in Discuss')
    reply = 'Received, thank you! Paying today.'
    f.type('typing', reply, ms=750, steps=8)
    f.hold(300, typing='', phone=f.state['phone'] + [{'side': 'out', 'text': reply, 'ticks': 2}])
    sent = {'author': 'Mitchell Admin', 'whatsapp': True, 'ticks': 3, 'text': INVOICE_TEXT,
            'pdf': 'INV-2026-00042.pdf'}
    f.hold(600, view='invoice', note=None, chatter=[sent])
    f.hold(2600, chatter=[{'author': 'Wood Corner', 'customer': True, 'whatsapp': True, 'text': reply}] +
           f.state['chatter'])
    f.hold(3200, end=True)
    return f


# ------------------------------------------------------------
# Banners: the title on the left, the moment of the module on a phone
# ------------------------------------------------------------

BW, BH = 1152, 648

BANNERS = {
    'om_whatsapp_base': {
        'spec': BASE, 'title': ['WhatsApp for', 'Odoo 20'],
        'subtitle': ['Templates, conversations in Discuss', 'and a log on every document'],
        'items': ['Free', 'Templates', 'Discuss', 'Any document'],
        'steps': [
            [],
            [{'side': 'out', 'text': 'Hello Wood Corner, here is your quotation S00042.', 'pdf': 'S00042.pdf',
              'ticks': 1}],
            [{'side': 'out', 'text': 'Hello Wood Corner, here is your quotation S00042.', 'pdf': 'S00042.pdf',
              'ticks': 3}],
            [{'side': 'out', 'text': 'Hello Wood Corner, here is your quotation S00042.', 'pdf': 'S00042.pdf',
              'ticks': 3}, {'side': 'in', 'text': "Thanks! Looks good, I'll confirm tomorrow."}],
        ],
        'toast': 'Logged on S00042.',
    },
    'om_whatsapp_web': {
        'spec': WEB, 'title': ['WhatsApp Web', 'in Odoo 20'],
        'subtitle': ['Chat with your customers from Odoo:', 'replies, reactions, PDFs, no API'],
        'items': ['Free', 'Chat & react', 'No API', 'Chrome & Firefox'],
        'steps': [
            [{'side': 'in', 'text': 'Hi! Is the oak table still available?'}],
            [{'side': 'in', 'text': 'Hi! Is the oak table still available?'},
             {'side': 'out', 'text': 'Yes, it is! I can deliver it on Friday.', 'ticks': 3}],
            [{'side': 'in', 'text': 'Hi! Is the oak table still available?'},
             {'side': 'out', 'text': 'Yes, it is! I can deliver it on Friday.', 'ticks': 3},
             {'side': 'in', 'text': "Perfect, I'll take it!", 'reaction': '👍'}],
            [{'side': 'in', 'text': 'Hi! Is the oak table still available?'},
             {'side': 'out', 'text': 'Yes, it is! I can deliver it on Friday.', 'ticks': 3},
             {'side': 'in', 'text': "Perfect, I'll take it!", 'reaction': '👍'},
             {'side': 'out', 'text': 'Your order S00042 is confirmed.', 'pdf': 'Order S00042.pdf', 'ticks': 3}],
        ],
        'toast': 'Order confirmed, WhatsApp sent.',
    },
    'om_whatsapp': {
        'spec': META, 'title': ['WhatsApp Cloud API', 'in Odoo 20'],
        'subtitle': ['The official API of Meta: templates, PDFs,', 'automation and replies, from the server'],
        'items': ['Official API', 'Automation', 'Templates', 'Two-way chat'],
        'steps': [
            [{'side': 'out', 'text': TEMPLATE_TEXT, 'pdf': 'Order S00051.pdf', 'ticks': 0, 'time': '02:14'}],
            [{'side': 'out', 'text': TEMPLATE_TEXT, 'pdf': 'Order S00051.pdf', 'ticks': 3, 'time': '02:14'}],
            [{'side': 'out', 'text': TEMPLATE_TEXT, 'pdf': 'Order S00051.pdf', 'ticks': 3, 'time': '02:14',
              'reaction': '👍'}],
            [{'side': 'out', 'text': TEMPLATE_TEXT, 'pdf': 'Order S00051.pdf', 'ticks': 3, 'time': '02:14',
              'reaction': '👍'}, {'side': 'in', 'text': 'Thanks! When will it arrive?', 'time': '08:05'}],
        ],
        'toast': 'Sent from the server at 02:14.',
    },
    'om_whatsapp_device': {
        'spec': DEVICE, 'title': ['WhatsApp QR', 'in Odoo 20'],
        'subtitle': ['Scan a QR code, and send from the server:', 'PDFs, automation and replies, no browser open'],
        'items': ['Scan & go', 'From the server', 'Automation', 'Two-way chat'],
        'steps': [
            [{'side': 'out', 'text': INVOICE_TEXT, 'pdf': 'INV-2026-00042.pdf', 'ticks': 0}],
            [{'side': 'out', 'text': INVOICE_TEXT, 'pdf': 'INV-2026-00042.pdf', 'ticks': 3}],
            [{'side': 'out', 'text': INVOICE_TEXT, 'pdf': 'INV-2026-00042.pdf', 'ticks': 3},
             {'side': 'in', 'text': 'Received, thank you! Paying today.'}],
        ],
        'toast': 'Sent from the server, no browser.',
    },
}


def banner_frame(spec, msgs, show_toast):
    c = Canvas((BW, BH))
    c.ellipse([-260, 380, 420, 1060], fill=SOFT)
    c.ellipse([820, -300, 1400, 240], fill=SOFT)
    c.rect([0, 0, BW, 8], fill=DARK)
    c.rect([0, BH - 8, BW * 0.62, BH], fill=DARK)
    c.rect([BW * 0.62, BH - 8, BW, BH], fill=GREEN)
    c.paste(module_icon(spec['spec']['badge'], 92), (60, 70))
    c.text((166, 88), 'ODOO MATES', 18, 'black', TEAL)
    c.text((166, 114), 'ODOO 20 COMMUNITY & ENTERPRISE', 13, 'bold', MUTED)
    y = 200
    for line in spec['title']:
        c.text((60, y), line, 54, 'black', DARK)
        y += 64
    y += 10
    for line in spec['subtitle']:
        c.text((60, y), line, 22, 'regular', MUTED)
        y += 32
    chips(c, 60, y + 26, spec['items'], 17)
    phone(c, [728, 40, 1092, 608], 'Wood Corner', msgs)
    if show_toast:
        toast(c, 60, 540, spec['toast'])
    return c.final()


def make_banner(path, spec):
    images, durations = [], []
    steps = spec['steps']
    for i, msgs in enumerate(steps):
        last = i == len(steps) - 1
        images.append(banner_frame(spec, msgs, last))
        durations.append(3400 if last else 1100)
    save_gif(path, images, durations)


# ------------------------------------------------------------

STORIES = {
    'om_whatsapp_base': film_base,
    'om_whatsapp_web': film_web,
    'om_whatsapp': film_meta,
    'om_whatsapp_device': film_device,
}


def main():
    wanted = sys.argv[1:] or list(STORIES)
    for module in wanted:
        target = os.path.join(assets.ODOOAPPS, module, 'static', 'description')
        count = STORIES[module]().save(os.path.join(target, 'story.gif'))
        make_banner(os.path.join(target, 'banner.gif'), BANNERS[module])
        size = os.path.getsize(os.path.join(target, 'story.gif')) / 1e6
        print(f'{module}: story.gif ({count} frames, {size:.1f} MB), banner.gif')


if __name__ == '__main__':
    main()
