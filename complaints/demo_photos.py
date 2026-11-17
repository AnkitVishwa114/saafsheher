# =============================================================================
# FILE: complaints/demo_photos.py
# WHAT IS HERE: draws the demo before/after street photos with Pillow (used by seed_demo).
# =============================================================================
"""
Draws believable street photos for demo data, so the app never needs stock images.

Each complaint gets a street scene (buildings, shop shutters, footpath, kerb, road) with the
problem drawn in: a garbage pile, an overflowing municipal bin, a choked drain, burning waste,
rubble, a dirty public toilet or litter all over the road. The "after" photo is the same street
(same seed) with the problem gone, a washed patch and lime powder where the pile was.
"""

import math
import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 880, 620          # drawn a little larger, then cropped like a phone photo
OUT = (800, 560)
GROUND = 300             # where the buildings meet the footpath
ROAD = 346               # where the road starts


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _street(rng, d, img, toilet=False, clean=False):
    top = rng.choice([(168, 199, 224), (198, 210, 220), (222, 204, 178), (186, 204, 214)])
    for y in range(GROUND):
        d.line([(0, y), (W, y)], fill=_mix(top, (238, 233, 222), y / GROUND))

    walls = [(214, 196, 160), (196, 176, 146), (228, 216, 192), (170, 188, 172), (204, 164, 142), (224, 202, 128), (182, 192, 206), (232, 226, 214)]
    boards = [(190, 52, 44), (28, 86, 150), (236, 186, 46), (36, 118, 78), (120, 40, 110)]
    x, toilet_x = -30, None
    while x < W:
        bw, bh = rng.randint(120, 210), rng.randint(150, 240)
        col, y0 = rng.choice(walls), GROUND - bh
        if toilet and toilet_x is None and x > W * 0.3:
            toilet_x = x
            _toilet_block(rng, d, x, bw, clean)
            x += bw + 4
            continue
        d.rectangle([x, y0, x + bw, GROUND], fill=col)
        d.rectangle([x, y0, x + bw, y0 + 6], fill=_mix(col, (60, 60, 55), 0.25))
        for _ in range(rng.randint(3, 6)):                               # rain stains
            sx = rng.randint(x, x + bw)
            d.rectangle([sx, y0 + rng.randint(8, 50), sx + rng.randint(4, 16), GROUND - rng.randint(0, 40)], fill=_mix(col, (80, 80, 70), 0.12))
        for wy in range(y0 + 18, 214, 46):                                # windows with grills
            for wx in range(x + 14, x + bw - 30, 42):
                d.rectangle([wx, wy, wx + 24, wy + 28], fill=(64, 74, 80))
                for gx in range(wx + 4, wx + 24, 6):
                    d.line([(gx, wy), (gx, wy + 28)], fill=(40, 46, 50))
                d.rectangle([wx - 3, wy + 28, wx + 27, wy + 31], fill=_mix(col, (255, 255, 255), 0.35))
        if rng.random() < 0.75:                                           # shop with rolling shutter
            sx0, sx1 = x + 10, x + bw - 10
            d.rectangle([sx0, 238, sx1, GROUND], fill=(148, 153, 156))
            for ly in range(240, GROUND, 5):
                d.line([(sx0, ly), (sx1, ly)], fill=(124, 129, 132))
            b = rng.choice(boards)
            d.rectangle([sx0 - 2, 218, sx1 + 2, 238], fill=b)
            for k in range(rng.randint(2, 4)):
                tx = sx0 + 8 + k * 26
                if tx + 18 < sx1:
                    d.rectangle([tx, 225, tx + 18, 231], fill=_mix(b, (255, 255, 255), 0.75))
        x += bw + rng.randint(0, 5)

    px = rng.randint(60, W - 60)                                          # electric pole + wires
    d.rectangle([px, 40, px + 9, ROAD - 10], fill=(118, 116, 108))
    d.rectangle([px - 22, 54, px + 31, 58], fill=(96, 94, 88))
    for k in range(4):
        d.line([(0, 70 + k * 9), (px, 58 + k * 2), (W, 84 + k * 11)], fill=(52, 52, 52), width=1)

    d.rectangle([0, GROUND, W, ROAD - 10], fill=(172, 166, 156))          # footpath tiles
    for fx in range(-40, W, 44):
        d.line([(fx, GROUND), (fx - 14, ROAD - 10)], fill=(152, 147, 139))
    d.line([(0, GROUND + 18), (W, GROUND + 18)], fill=(156, 151, 143))
    for fx in range(0, W, 56):                                            # painted kerb
        d.rectangle([fx, ROAD - 10, fx + 28, ROAD], fill=(232, 192, 48))
        d.rectangle([fx + 28, ROAD - 10, fx + 56, ROAD], fill=(34, 34, 34))
    for y in range(ROAD, H):                                              # road
        d.line([(0, y), (W, y)], fill=_mix((116, 115, 110), (84, 84, 82), (y - ROAD) / (H - ROAD)))
    for _ in range(2600):
        rx, ry, c = rng.randint(0, W), rng.randint(ROAD, H), rng.randint(66, 136)
        d.point((rx, ry), fill=(c, c, c - 3))
    for _ in range(rng.randint(2, 4)):                                    # tar patches
        cx, cy = rng.randint(0, W), rng.randint(ROAD + 30, H - 30)
        d.ellipse([cx, cy, cx + rng.randint(70, 160), cy + rng.randint(16, 34)], fill=(96, 95, 92))
    d.line([(0, H - 70), (W, H - 64)], fill=(214, 210, 196), width=4)     # faded lane line
    return toilet_x


def _toilet_block(rng, d, x, bw, clean=False):
    d.rectangle([x, 150, x + bw, GROUND], fill=(204, 222, 230))
    d.rectangle([x, 150, x + bw, 168], fill=(40, 96, 150))
    d.text((x + 12, 153), "PUBLIC TOILET", fill=(255, 255, 255), font=_font(13))
    for k, dx in enumerate((18, bw // 2 + 4)):
        d.rectangle([x + dx, 196, x + dx + bw // 2 - 26, GROUND], fill=(120, 140, 150))
        d.text((x + dx + 8, 204), "GENTS" if k == 0 else "LADIES", fill=(240, 240, 240), font=_font(11))
    for _ in range(14):                                                   # stains and seepage
        sx, sy = rng.randint(x, x + bw), rng.randint(200, GROUND)
        box, tint = [sx, sy, sx + rng.randint(8, 30), sy + rng.randint(10, 40)], rng.choice([(150, 128, 70), (120, 104, 60), (170, 150, 90)])
        if not clean:
            d.ellipse(box, fill=tint)
    if not clean:
        d.ellipse([x - 30, GROUND + 6, x + bw + 40, GROUND + 40], fill=(90, 92, 70))


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                     # very old Pillow
        return ImageFont.load_default()


LITTER = [(236, 236, 230), (64, 110, 186), (34, 34, 38), (222, 122, 150), (88, 150, 80), (226, 214, 186), (122, 88, 50), (172, 130, 80), (210, 70, 60), (240, 200, 60)]


def _blob(rng, d, x, y, s, col):
    pts = []
    for k in range(7):
        a = k / 7 * 6.283 + rng.uniform(-0.3, 0.3)
        r = s * rng.uniform(0.6, 1.1)
        pts.append((x + r * 1.25 * math.cos(a), y + r * 0.8 * math.sin(a)))
    d.polygon(pts, fill=col)
    if col == (34, 34, 38) or col == (64, 110, 186):                      # plastic shine
        d.line([(x - s * 0.4, y - s * 0.3), (x + s * 0.1, y - s * 0.5)], fill=_mix(col, (255, 255, 255), 0.45), width=2)


def _pile(rng, d, cx, cy, size, n=90, colors=LITTER):
    d.ellipse([cx - size * 1.25, cy - size * 0.18, cx + size * 1.25, cy + size * 0.28], fill=(62, 58, 50))
    for i in range(n):
        dx = rng.gauss(0, size * 0.5)
        h = max(0, 1 - abs(dx) / (size * 1.2))
        dy = -abs(rng.gauss(0, size * 0.42)) * h
        _blob(rng, d, cx + dx, cy + dy, rng.uniform(11, 30) * (0.6 + h * 0.6), rng.choice(colors))
    for _ in range(26):                                                   # stray litter around
        lx, ly = cx + rng.uniform(-size * 2.4, size * 2.4), cy + rng.uniform(-10, 60)
        _blob(rng, d, lx, ly, rng.uniform(3, 8), rng.choice(colors))


def _bin(rng, d, cx, cy):
    _pile(rng, d, cx + 50, cy + 10, 70, n=50)
    d.polygon([(cx - 90, cy - 120), (cx + 90, cy - 120), (cx + 74, cy), (cx - 74, cy)], fill=(34, 112, 66))
    d.rectangle([cx - 94, cy - 128, cx + 94, cy - 116], fill=(26, 90, 52))
    d.text((cx - 54, cy - 80), "NAGAR NIGAM", fill=(240, 240, 230), font=_font(16))
    d.text((cx - 30, cy - 58), "Dry / Wet", fill=(210, 230, 210), font=_font(12))
    _pile(rng, d, cx, cy - 128, 66, n=60)                                 # overflowing top


def _drain(rng, d, cx, cy):
    pts = [(cx - 220, ROAD + 6), (cx + 240, ROAD + 4), (cx + 200, cy + 50), (cx - 30, cy + 70), (cx - 240, cy + 30)]
    d.polygon(pts, fill=(52, 58, 48))
    for _ in range(18):                                                   # sky reflection streaks
        sx, sy = rng.randint(cx - 200, cx + 180), rng.randint(ROAD + 14, cy + 40)
        d.line([(sx, sy), (sx + rng.randint(20, 60), sy)], fill=(120, 132, 130), width=1)
    d.rectangle([cx - 60, ROAD - 8, cx + 60, ROAD + 6], fill=(40, 40, 40))
    for gx in range(cx - 56, cx + 60, 9):
        d.line([(gx, ROAD - 8), (gx, ROAD + 6)], fill=(90, 90, 90), width=2)
    for _ in range(40):
        _blob(rng, d, rng.randint(cx - 200, cx + 200), rng.randint(ROAD + 10, cy + 50), rng.uniform(4, 11), rng.choice(LITTER))


def _fire(rng, img, d, cx, cy):
    _pile(rng, d, cx, cy, 90, n=70, colors=[(40, 36, 32), (70, 60, 50), (110, 100, 90), (34, 34, 38), (150, 140, 120)])
    for _ in range(26):
        fx, fh = cx + rng.gauss(0, 50), rng.uniform(30, 90)
        w = rng.uniform(10, 22)
        d.polygon([(fx - w, cy - 30), (fx, cy - 30 - fh), (fx + w, cy - 30)], fill=rng.choice([(240, 120, 30), (250, 170, 40), (230, 80, 30), (255, 210, 90)]))
    smoke = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(smoke)
    for k in range(22):
        sx, sy = cx + rng.gauss(0, 40) + k * 6, cy - 90 - k * 18
        r = 30 + k * 4
        g = rng.randint(120, 170)
        sd.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(g, g, g, 70))
    img.paste(Image.alpha_composite(img.convert("RGBA"), smoke.filter(ImageFilter.GaussianBlur(14))).convert("RGB"))


def _debris(rng, d, cx, cy):
    d.ellipse([cx - 210, cy - 40, cx + 170, cy + 50], fill=(170, 150, 120))           # sand
    for _ in range(80):
        x, y, s = cx + rng.gauss(0, 90), cy - abs(rng.gauss(0, 34)), rng.uniform(8, 22)
        if rng.random() < 0.45:
            d.polygon([(x, y), (x + s * 1.6, y + rng.uniform(-4, 4)), (x + s * 1.6, y + s * 0.8), (x, y + s * 0.8)], fill=rng.choice([(168, 70, 50), (150, 60, 44), (186, 88, 62)]))
        else:
            _blob(rng, d, x, y, s, rng.choice([(150, 150, 146), (124, 124, 120), (180, 178, 170), (100, 98, 94)]))


def _litter_road(rng, d):
    for _ in range(170):
        x, y = rng.randint(0, W), rng.randint(GROUND + 4, H - 4)
        _blob(rng, d, x, y, rng.uniform(3, 9), rng.choice(LITTER + [(140, 110, 50), (170, 140, 60)]))


def _carcass(rng, d, cx, cy):
    d.ellipse([cx - 90, cy - 26, cx + 90, cy + 24], fill=(88, 76, 60))
    d.polygon([(cx - 100, cy - 6), (cx - 40, cy - 46), (cx + 70, cy - 40), (cx + 106, cy + 4), (cx - 60, cy + 18)], fill=(176, 150, 104))   # gunny sack over it
    for k in range(5):
        d.line([(cx - 70 + k * 30, cy - 40), (cx - 80 + k * 30, cy + 12)], fill=(150, 126, 84), width=2)
    for _ in range(30):
        fx, fy = cx + rng.gauss(0, 70), cy - 60 + rng.gauss(0, 30)
        d.point((fx, fy), fill=(20, 20, 20)); d.point((fx + 1, fy), fill=(20, 20, 20))


DRAW = {
    "garbage-pile": "pile", "overflowing-dustbin": "bin", "blocked-drain": "drain", "burning-garbage": "fire",
    "dead-animal": "carcass", "construction-debris": "debris", "dirty-public-toilet": "toilet", "street-not-swept": "litter",
}


def _finish(img, rng, stamp):
    x0, y0 = rng.randint(0, W - OUT[0]), rng.randint(0, H - OUT[1])
    img = img.crop((x0, y0, x0 + OUT[0], y0 + OUT[1])).filter(ImageFilter.GaussianBlur(0.7))
    noise = Image.effect_noise(OUT, 22).convert("RGB")
    img = Image.blend(img, noise, 0.05)
    img = ImageEnhance.Color(img).enhance(rng.uniform(0.9, 1.15))
    img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.92, 1.06))
    vign = Image.new("L", OUT, 0)
    ImageDraw.Draw(vign).ellipse([-120, -110, OUT[0] + 120, OUT[1] + 110], fill=255)
    img = Image.composite(img, Image.new("RGB", OUT, (30, 30, 28)), vign.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(img)
    f = _font(20)
    d.text((OUT[0] - 206, OUT[1] - 36), stamp, fill=(0, 0, 0), font=f)
    d.text((OUT[0] - 208, OUT[1] - 38), stamp, fill=(255, 164, 40), font=f)
    out = BytesIO()
    img.save(out, "JPEG", quality=84, optimize=True)
    return out.getvalue()


def make(slug, seed, before_stamp, after_stamp=None):
    """Return (before_jpeg_bytes, after_jpeg_bytes or None) for a category slug."""
    kind = DRAW.get(slug, "pile")
    shots = []
    for clean in (False, True):
        if clean and after_stamp is None:
            break
        rng = random.Random(seed)
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        _street(rng, d, img, toilet=(kind == "toilet"), clean=clean)
        prob = random.Random(seed * 7 + 1)
        cx, cy = prob.randint(260, W - 260), prob.randint(ROAD + 30, ROAD + 120)
        if not clean:
            if kind == "pile":
                _pile(prob, d, cx, cy, prob.randint(85, 120), n=130)
            elif kind == "bin":
                _bin(prob, d, cx, cy + 20)
            elif kind == "drain":
                _drain(prob, d, cx, cy)
            elif kind == "fire":
                _fire(prob, img, d, cx, cy)
                d = ImageDraw.Draw(img)
            elif kind == "debris":
                _debris(prob, d, cx, cy)
            elif kind == "litter":
                _litter_road(prob, d)
            elif kind == "carcass":
                _carcass(prob, d, cx, cy)
            elif kind == "toilet":
                _pile(prob, d, cx, cy + 30, 40, n=30)
        else:
            d.ellipse([cx - 150, cy - 18, cx + 150, cy + 40], fill=(98, 98, 96))          # washed, still damp
            for _ in range(160):                                                         # lime powder
                lx, ly = cx + prob.gauss(0, 90), cy + prob.gauss(8, 10)
                d.point((lx, ly), fill=(236, 236, 228))
            if kind in ("bin", "pile"):
                bx = cx + 170
                d.polygon([(bx - 40, cy - 70), (bx + 40, cy - 70), (bx + 32, cy), (bx - 32, cy)], fill=(34, 112, 66))
                d.rectangle([bx - 44, cy - 76, bx + 44, cy - 68], fill=(26, 90, 52))
        shots.append(_finish(img, random.Random(seed * 3 + (5 if clean else 0)), after_stamp if clean else before_stamp))
    return shots[0], (shots[1] if len(shots) > 1 else None)
