#!/usr/bin/env python3
"""BenillaPad's art, drawn from scratch: no external images, no imaging libraries.

    python3 crates/benilla-pad/tools/gen_art.py [--preview <png>]

Writes 32-bit TGAs (bottom-left origin, the form 1.12 loads) into addon/BenillaPad/Art:

- Ring.tga        the round slot's metal ring, neutral grey (the Lua tints it bronze); drawn at
                  1.3x the button, so the band (radius 0.66-0.84 of the texture) covers the
                  round icon's edge at 0.69
- RingSelect.tga  the gold press / selection ring, same geometry
- Disc.tga        a soft white disc (badges, shadows, the wheel's backdrop)
- AutoRun.tga, Wheel.tga, Menu.tga  game-action icons, 64x64

Shapes are signed distance functions sampled 4x4 per pixel.
"""

import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "addon", "BenillaPad", "Art")
SS = 4  # supersamples per axis


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(edge0, edge1, x):
    t = clamp((x - edge0) / (edge1 - edge0))
    return t * t * (3 - 2 * t)


def over(dst, src):
    """Source-over of two straight-alpha RGBA tuples (0..1)."""
    sa = src[3]
    da = dst[3]
    a = sa + da * (1 - sa)
    if a <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    return tuple((src[i] * sa + dst[i] * da * (1 - sa)) / a for i in range(3)) + (a,)


def render(size, shade):
    """An image of size x size: `shade(x, y)` gives RGBA at a point of [-1, 1]^2 (y up),
    averaged over SS x SS samples. Rows top to bottom."""
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            acc = [0.0, 0.0, 0.0, 0.0]
            for sy in range(SS):
                for sx in range(SS):
                    x = ((px + (sx + 0.5) / SS) / size) * 2 - 1
                    y = 1 - ((py + (sy + 0.5) / SS) / size) * 2
                    r, g, b, a = shade(x, y)
                    acc[0] += r * a
                    acc[1] += g * a
                    acc[2] += b * a
                    acc[3] += a
            n = SS * SS
            a = acc[3] / n
            if a > 0:
                row.append((acc[0] / acc[3], acc[1] / acc[3], acc[2] / acc[3], a))
            else:
                row.append((0.0, 0.0, 0.0, 0.0))
        rows.append(row)
    return rows


def write_tga(path, rows):
    h = len(rows)
    w = len(rows[0])
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 8)
    body = bytearray()
    for row in reversed(rows):  # bottom-left origin
        for r, g, b, a in row:
            body += bytes((round(clamp(b) * 255), round(clamp(g) * 255), round(clamp(r) * 255),
                           round(clamp(a) * 255)))
    with open(path, "wb") as f:
        f.write(header + body)


def write_png(path, rows):
    h = len(rows)
    w = len(rows[0])
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for r, g, b, a in row:
            raw += bytes((round(clamp(r) * 255), round(clamp(g) * 255), round(clamp(b) * 255),
                          round(clamp(a) * 255)))

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ── Signed distances (negative inside) ──

def sd_circle(x, y, cx, cy, r):
    return math.hypot(x - cx, y - cy) - r


def sd_box(x, y, cx, cy, hw, hh, rad=0.0):
    qx = abs(x - cx) - hw + rad
    qy = abs(y - cy) - hh + rad
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - rad


def sd_segment(x, y, ax, ay, bx, by, r):
    px, py = x - ax, y - ay
    dx, dy = bx - ax, by - ay
    t = clamp((px * dx + py * dy) / (dx * dx + dy * dy))
    return math.hypot(px - dx * t, py - dy * t) - r


def fill(d, aa=0.012):
    """Coverage of a signed distance, with a small soft edge."""
    return 1 - smooth(-aa, aa, d)


# ── The rings ──

IN, OUT = 0.66, 0.84


def ring(x, y):
    r = math.hypot(x, y)
    out = (0.0, 0.0, 0.0, 0.0)
    # A soft drop shadow outside the band.
    shadow = (1 - smooth(OUT, 0.98, r)) * smooth(IN, OUT, r) * 0.55
    out = over(out, (0.0, 0.0, 0.0, shadow))
    band = fill(IN - r) * fill(r - OUT)
    if band > 0:
        # Light from the top left: the bevel's profile across the band, lit by the angle.
        t = (r - IN) / (OUT - IN)
        profile = 0.55 + 0.45 * math.sin(t * math.pi)
        angle = math.atan2(y, x)
        light = 0.75 + 0.25 * math.cos(angle - math.radians(135))
        v = clamp(profile * light)
        # A bright inner lip and a dark outer edge.
        lip = 1 - smooth(0.0, 0.12, t)
        edge = smooth(0.85, 1.0, t)
        v = clamp(v + 0.25 * lip - 0.45 * edge)
        out = over(out, (v, v, v, band))
    return out


def ring_select(x, y):
    r = math.hypot(x, y)
    # A gold band with a glow that fades out to the edge.
    glow = (1 - smooth(OUT, 1.0, r)) * smooth(IN - 0.08, IN, r) * 0.6
    out = (1.0, 0.78, 0.18, glow)
    band = fill(IN - 0.02 - r) * fill(r - (OUT - 0.02))
    if band > 0:
        t = (r - (IN - 0.02)) / (OUT - IN)
        v = 0.7 + 0.3 * math.sin(clamp(t) * math.pi)
        out = over(out, (1.0, 0.82 * v + 0.1, 0.25 * v, band))
    return out


def disc(x, y):
    return (1.0, 1.0, 1.0, fill(math.hypot(x, y) - 0.94, 0.04))


# ── The icons ──

def icon_base(x, y):
    """A dark slate tile with a light top and a thin border, behind every icon."""
    d = sd_box(x, y, 0, 0, 0.98, 0.98, 0.18)
    a = fill(d, 0.02)
    top = 0.5 + 0.5 * y
    col = (0.06 + 0.07 * top, 0.09 + 0.09 * top, 0.15 + 0.12 * top, a)
    border = fill(abs(d + 0.05) - 0.025, 0.02) * a
    return over(col, (0.55, 0.62, 0.75, border * 0.8))


WHITE = (0.96, 0.96, 0.92)
GOLD = (1.0, 0.82, 0.25)


def icon(symbol):
    def shade(x, y):
        out = icon_base(x, y)
        cov, colour = symbol(x, y)
        # A dark outline under the symbol, then the symbol.
        out = over(out, (0.0, 0.0, 0.0, cov[1] * 0.7))
        return over(out, colour + (cov[0],))
    return shade


def autorun(x, y):
    # Two chevrons pointing right.
    d = min(
        min(sd_segment(x, y, -0.55, 0.45, -0.1, 0.0, 0.11), sd_segment(x, y, -0.1, 0.0, -0.55, -0.45, 0.11)),
        min(sd_segment(x, y, 0.0, 0.45, 0.45, 0.0, 0.11), sd_segment(x, y, 0.45, 0.0, 0.0, -0.45, 0.11)),
    )
    return (fill(d), fill(d - 0.06)), WHITE


def wheel(x, y):
    # Eight dots round a ring, one of them gold, and a hub.
    d = sd_circle(x, y, 0, 0, 0.14)
    gold = 1e9
    for i in range(8):
        a = math.radians(90 - i * 45)
        dd = sd_circle(x, y, 0.58 * math.cos(a), 0.58 * math.sin(a), 0.13)
        if i == 0:
            gold = dd
        else:
            d = min(d, dd)
    cov = fill(min(d, gold))
    halo = fill(min(d, gold) - 0.06)
    colour = GOLD if gold < d and gold < 0.05 else WHITE
    return (cov, halo), colour


def menu(x, y):
    # A gamepad: a rounded body with two grips, then the D-pad and face buttons cut out.
    body = min(sd_box(x, y, 0, 0.08, 0.62, 0.3, 0.28),
               sd_circle(x, y, -0.48, -0.2, 0.3), sd_circle(x, y, 0.48, -0.2, 0.3))
    dpad = min(sd_box(x, y, -0.42, 0.05, 0.16, 0.05), sd_box(x, y, -0.42, 0.05, 0.05, 0.16))
    face = min(sd_circle(x, y, 0.42, 0.18, 0.06), sd_circle(x, y, 0.42, -0.08, 0.06),
               sd_circle(x, y, 0.29, 0.05, 0.06), sd_circle(x, y, 0.55, 0.05, 0.06))
    d = max(body, -min(dpad, face))
    return (fill(d), fill(body - 0.06)), WHITE


ART_FILES = {
    "Ring.tga": (128, ring),
    "RingSelect.tga": (128, ring_select),
    "Disc.tga": (64, disc),
    "AutoRun.tga": (64, icon(autorun)),
    "Wheel.tga": (64, icon(wheel)),
    "Menu.tga": (64, icon(menu)),
}


def main():
    os.makedirs(ART, exist_ok=True)
    images = {}
    for name, (size, shade) in ART_FILES.items():
        rows = render(size, shade)
        write_tga(os.path.join(ART, name), rows)
        images[name] = rows
        print("wrote", name)
    if "--preview" in sys.argv:
        # Every image on a mid-grey sheet, at 128 px each.
        path = sys.argv[sys.argv.index("--preview") + 1]
        cell = 128
        sheet = [[(0.32, 0.34, 0.3, 1.0)] * (cell * len(images)) for _ in range(cell)]
        for k, rows in enumerate(images.values()):
            n = len(rows)
            for py in range(cell):
                for px in range(cell):
                    src = rows[py * n // cell][px * n // cell]
                    sheet[py][k * cell + px] = over(sheet[py][k * cell + px], src)
        write_png(path, sheet)
        print("preview", path)


if __name__ == "__main__":
    main()
