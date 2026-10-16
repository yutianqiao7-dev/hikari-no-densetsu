# -*- coding: utf-8 -*-
"""
ひかりの伝説 — 服の模様（刺しゅう・帯・紋章・インクの線）を描く

布の大きさ（m）で座標をとり、numpy で描く。Y = 0 が布の上端、Y が増えるほど下。
to_image() で Blender の画像（sRGB）にする。Blender の外でも save_png() で確かめられる。
"""
import math
import numpy as np

INK = (0.1, 0.07, 0.12)


def lin(c):
    return np.array([v ** 2.2 for v in c])


class Canvas:
    def __init__(self, w, h, wm, hm, base):
        self.w, self.h, self.wm, self.hm = w, h, wm, hm
        self.sx = w / wm
        self.sy = h / hm
        self.rgb = np.ones((h, w, 3)) * lin(base)

    # 窓（描くところだけ計算して速く）
    def _win(self, x0, y0, x1, y1):
        i0 = max(int(math.floor(y0 * self.sy)) - 2, 0)
        i1 = min(int(math.ceil(y1 * self.sy)) + 2, self.h)
        j0 = max(int(math.floor(x0 * self.sx)) - 2, 0)
        j1 = min(int(math.ceil(x1 * self.sx)) + 2, self.w)
        if i0 >= i1 or j0 >= j1:
            return None
        Y, X = np.mgrid[i0:i1, j0:j1].astype(np.float64)
        return (slice(i0, i1), slice(j0, j1), (X + 0.5) / self.sx, (Y + 0.5) / self.sy)

    def _blend(self, win, cov, col):
        si, sj = win[0], win[1]
        c = lin(col)
        self.rgb[si, sj] = self.rgb[si, sj] * (1 - cov[..., None]) + c * cov[..., None]

    def _px(self):
        return 1.0 / self.sx

    def line(self, pts, widths, col, a=1.0):
        if isinstance(widths, (int, float)):
            widths = [widths] * len(pts)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        mw = max(widths)
        win = self._win(min(xs) - mw, min(ys) - mw, max(xs) + mw, max(ys) + mw)
        if win is None:
            return
        X, Y = win[2], win[3]
        best = np.full(X.shape, 1e9)
        wb = np.zeros(X.shape)
        for (p0, p1, w0, w1) in zip(pts[:-1], pts[1:], widths[:-1], widths[1:]):
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            L2 = dx * dx + dy * dy + 1e-12
            t = np.clip(((X - p0[0]) * dx + (Y - p0[1]) * dy) / L2, 0, 1)
            d = np.sqrt((X - p0[0] - dx * t) ** 2 + (Y - p0[1] - dy * t) ** 2)
            wv = w0 + (w1 - w0) * t
            m = d - wv * 0.5 < best - wb * 0.5
            best = np.where(m, d, best)
            wb = np.where(m, wv, wb)
        cov = np.clip((wb * 0.5 - best) / (self._px() * 1.1) + 0.5, 0, 1) * a
        self._blend(win, cov, col)

    def shape(self, cx, cy, R, rfun, col, a=1.0, outline=None, ow=0.0):
        """極座標で決めた形を塗る（rfun(角度) = 半径の倍率）"""
        win = self._win(cx - R * 1.2, cy - R * 1.2, cx + R * 1.2, cy + R * 1.2)
        if win is None:
            return
        X, Y = win[2] - cx, win[3] - cy
        r = np.sqrt(X * X + Y * Y)
        ang = np.arctan2(Y, X)
        lim = R * rfun(ang)
        cov = np.clip((lim - r) / (self._px() * 1.1) + 0.5, 0, 1) * a
        if outline is not None:
            ocov = np.clip((lim + ow * 0.5 - r) / (self._px() * 1.1) + 0.5, 0, 1) * a
            self._blend(win, ocov, outline)
        self._blend(win, cov, col)

    def disc(self, cx, cy, r, col, a=1.0, outline=None, ow=0.0):
        self.shape(cx, cy, r, lambda ang: np.ones_like(ang), col, a, outline, ow)

    def ellipse(self, cx, cy, rx, ry, rot, col, a=1.0, outline=None, ow=0.0):
        c, s = math.cos(rot), math.sin(rot)
        R = max(rx, ry)

        def rf(ang):
            # 回した楕円の、その角度での半径
            t = ang - rot
            return 1.0 / np.sqrt((np.cos(t) * R / rx) ** 2 + (np.sin(t) * R / ry) ** 2)
        self.shape(cx, cy, R, rf, col, a, outline, ow)

    def polygon(self, pts, col, a=1.0, outline=None, ow=0.0):
        """多角形を塗る（ふちはなめらかに）"""
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        win = self._win(min(xs) - ow, min(ys) - ow, max(xs) + ow, max(ys) + ow)
        if win is None:
            return
        X, Y = win[2], win[3]
        inside = np.zeros(X.shape, bool)
        dmin = np.full(X.shape, 1e9)
        n = len(pts)
        for k in range(n):
            (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % n]
            cond = (y0 > Y) != (y1 > Y)
            xc = x0 + (Y - y0) * (x1 - x0) / (y1 - y0 + 1e-12)
            inside ^= cond & (X < xc)
            dx, dy = x1 - x0, y1 - y0
            t = np.clip(((X - x0) * dx + (Y - y0) * dy) / (dx * dx + dy * dy + 1e-12), 0, 1)
            dmin = np.minimum(dmin, np.sqrt((X - x0 - dx * t) ** 2 + (Y - y0 - dy * t) ** 2))
        sd = np.where(inside, -dmin, dmin)      # 内側が負
        p = self._px() * 1.1
        if outline is not None:
            self._blend(win, np.clip((ow * 0.5 - sd) / p + 0.5, 0, 1) * a, outline)
        self._blend(win, np.clip(-sd / p + 0.5, 0, 1) * a, col)

    def star(self, cx, cy, r, col, a=1.0, n=5, outline=None, ow=0.0):
        pts = []
        for k in range(n * 2):
            ang = -math.pi / 2 + k * math.pi / n
            rr = r if k % 2 == 0 else r * 0.42
            pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
        self.polygon(pts, col, a, outline, ow)

    def moon(self, cx, cy, r, col, bg, a=1.0):
        """三日月：円を塗り、少しずらした円を地の色で重ねて欠けさせる"""
        self.disc(cx, cy, r, col, a)
        self.disc(cx + r * 0.45, cy - r * 0.2, r * 0.85, bg, a)

    def rect(self, x0, y0, x1, y1, col, a=1.0):
        win = self._win(x0, y0, x1, y1)
        if win is None:
            return
        X, Y = win[2], win[3]
        p = self._px()
        cov = (np.clip((X - x0) / p + 0.5, 0, 1) * np.clip((x1 - X) / p + 0.5, 0, 1) *
               np.clip((Y - y0) / p + 0.5, 0, 1) * np.clip((y1 - Y) / p + 0.5, 0, 1)) * a
        self._blend(win, cov, col)

    def cross(self, cx, cy, s, col, outline=INK):
        w = s * 0.32
        self.rect(cx - w / 2 - 0.0015, cy - s / 2 - 0.0015, cx + w / 2 + 0.0015, cy + s / 2 + 0.0015, outline)
        self.rect(cx - s / 2 - 0.0015, cy - w / 2 - 0.0015, cx + s / 2 + 0.0015, cy + w / 2 + 0.0015, outline)
        self.rect(cx - w / 2, cy - s / 2, cx + w / 2, cy + s / 2, col)
        self.rect(cx - s / 2, cy - w / 2, cx + s / 2, cy + w / 2, col)

    def wing(self, cx, cy, s, flip, fill, line):
        """羽根（5 枚の羽を扇に）"""
        for k in range(5):
            ang = math.radians(-10 + k * 22) * flip
            L = s * (1.0 - k * 0.12)
            ex = cx + math.cos(ang) * L * flip
            ey = cy - math.sin(abs(ang)) * L * 0.6 - k * s * 0.08
            mx, my = (cx + ex) / 2, (cy + ey) / 2
            rot = math.atan2(ey - cy, ex - cx)
            self.ellipse(mx, my, L * 0.55, s * 0.13, rot, fill, outline=line, ow=0.0025)

    def vine(self, x0, y0, x1, y1, col, leaf, amp=0.02, waves=3, leaves=8, w=0.0025):
        pts = []
        n = 40
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) + 1e-9
        nx, ny = -dy / L, dx / L
        for i in range(n + 1):
            t = i / n
            o = math.sin(t * math.pi * 2 * waves) * amp
            pts.append((x0 + dx * t + nx * o, y0 + dy * t + ny * o))
        self.line(pts, w, col)
        for i in range(leaves):
            t = (i + 0.5) / leaves
            o = math.sin(t * math.pi * 2 * waves) * amp
            px, py = x0 + dx * t + nx * o, y0 + dy * t + ny * o
            sd = 1 if i % 2 == 0 else -1
            ang = math.atan2(dy, dx) + sd * 0.9
            lx, ly = px + math.cos(ang) * amp * 0.9, py + math.sin(ang) * amp * 0.9
            self.ellipse(lx, ly, amp * 0.75, amp * 0.3, ang, leaf, outline=col, ow=w * 0.6)

    def rune(self, cx, cy, s, seed, col, w=0.002):
        rng = np.random.default_rng(seed)
        kind = seed % 6
        h = s / 2
        if kind == 0:
            self.line([(cx, cy - h), (cx, cy + h)], w, col)
            self.line([(cx, cy - h * 0.6), (cx + h * 0.6, cy - h * 0.1)], w, col)
        elif kind == 1:
            self.line([(cx - h * 0.5, cy + h), (cx, cy - h), (cx + h * 0.5, cy + h)], w, col)
            self.line([(cx - h * 0.3, cy + h * 0.2), (cx + h * 0.3, cy + h * 0.2)], w, col)
        elif kind == 2:
            self.line([(cx, cy - h), (cx, cy + h)], w, col)
            self.line([(cx, cy - h), (cx + h * 0.55, cy - h * 0.5), (cx, cy)], w, col)
        elif kind == 3:
            self.line([(cx - h * 0.5, cy - h), (cx + h * 0.5, cy + h)], w, col)
            self.line([(cx + h * 0.5, cy - h), (cx - h * 0.5, cy + h)], w, col)
        elif kind == 4:
            self.line([(cx - h * 0.4, cy - h), (cx - h * 0.4, cy + h)], w, col)
            self.line([(cx + h * 0.4, cy - h), (cx + h * 0.4, cy + h)], w, col)
            self.line([(cx - h * 0.4, cy - h * 0.2), (cx + h * 0.4, cy + h * 0.3)], w, col)
        else:
            self.line([(cx, cy - h), (cx + h * 0.5, cy), (cx, cy + h), (cx - h * 0.5, cy), (cx, cy - h)], w, col)

    def band(self, y0, y1, col, edge=INK, ew=0.003):
        self.rect(0, y0, self.wm, y1, col)
        self.rect(0, y0 - ew / 2, self.wm, y0 + ew / 2, edge)
        self.rect(0, y1 - ew / 2, self.wm, y1 + ew / 2, edge)

    def vband(self, x0, x1, col, edge=INK, ew=0.003, y0=0.0, y1=None):
        y1 = self.hm if y1 is None else y1
        self.rect(x0, y0, x1, y1, col)
        self.rect(x0 - ew / 2, y0, x0 + ew / 2, y1, edge)
        self.rect(x1 - ew / 2, y0, x1 + ew / 2, y1, edge)

    def folds(self, n, col, rng, y0=0.15, y1=1.0, a=0.2, w=0.0025):
        """布のしわの線（上から下へ、ゆるい曲線で、両端は細く）"""
        for i in range(n):
            x = rng.uniform(0, self.wm)
            ya = self.hm * rng.uniform(y0, 0.5)
            yb = self.hm * rng.uniform(0.6, y1)
            bend = rng.uniform(-0.025, 0.025)
            pts, ws = [], []
            for k in range(17):
                t = k / 16
                pts.append((x + bend * math.sin(t * math.pi) + bend * 0.4 * t, ya + (yb - ya) * t))
                ws.append(w * (0.2 + 0.8 * math.sin(t * math.pi)))
            self.line(pts, ws, col, a)

    def pixels(self):
        out = np.flipud(np.clip(self.rgb, 0, 1)) ** (1 / 2.2)
        return np.concatenate([out, np.ones(out.shape[:2] + (1,))], -1).astype(np.float32)

    def to_image(self, name):
        import bpy
        old = bpy.data.images.get(name)
        if old:
            bpy.data.images.remove(old)
        img = bpy.data.images.new(name, self.w, self.h, alpha=False)
        img.pixels.foreach_set(self.pixels().ravel())
        img.pack()
        return img

    def save_png(self, path):
        from PIL import Image
        im = (np.flipud(self.pixels())[..., :3] * 255).astype(np.uint8)
        Image.fromarray(im).save(path)


# ================================================================ 服ごとの模様
GOLD = (0.95, 0.72, 0.25)


def serena_overskirt(w=2048, h=1024):
    """セレナの上掛け：青地に つたの刺しゅう、すその水色の帯に金の十字と白い羽根、縁取り"""
    blue, light, navy = (0.15, 0.3, 0.68), (0.4, 0.58, 0.9), (0.06, 0.1, 0.28)
    c = Canvas(w, h, 1.9, 0.95, blue)
    rng = np.random.default_rng(3)
    c.folds(26, navy, rng, a=0.25)
    # 前のふち（左右の端）の帯とつた
    for x0, x1 in ((0.0, 0.07), (1.83, 1.9)):
        c.vband(x0, x1, light, edge=navy)
    for xs in (0.12, 1.78):
        c.vine(xs, 0.05, xs, 0.75, (0.62, 0.78, 1.0), (0.5, 0.68, 0.95), amp=0.022, waves=4, leaves=12)
    # すその帯
    c.band(0.78, 0.9, light, edge=navy)
    x = 0.06
    k = 0
    while x < 1.88:
        if k % 2 == 0:
            c.cross(x, 0.84, 0.05, GOLD, outline=navy)
        else:
            c.wing(x - 0.004, 0.85, 0.035, -1, (0.98, 0.98, 1.0), navy)
            c.wing(x + 0.004, 0.85, 0.035, 1, (0.98, 0.98, 1.0), navy)
        x += 0.085
        k += 1
    return c


def serena_tabard(w=512, h=2048):
    """セレナの白い前掛け：胸に羽根の紋章、しわの線"""
    white, line = (0.97, 0.97, 0.99), (0.55, 0.6, 0.75)
    c = Canvas(w, h, 0.22, 0.88, white)
    rng = np.random.default_rng(5)
    c.folds(10, line, rng, y0=0.25, a=0.35, w=0.002)
    c.wing(0.104, 0.09, 0.05, -1, (0.99, 0.99, 1.0), line)
    c.wing(0.116, 0.09, 0.05, 1, (0.99, 0.99, 1.0), line)
    c.cross(0.11, 0.155, 0.04, GOLD, outline=(0.45, 0.32, 0.12))
    c.vine(0.11, 0.2, 0.11, 0.45, (0.6, 0.7, 0.9), (0.75, 0.82, 0.95), amp=0.015, waves=2, leaves=6, w=0.0018)
    return c


def milia_band_runes(c, y0, y1, green, gold, seed=1):
    c.band(y0, y1, green, edge=(0.06, 0.16, 0.12))
    x = 0.03
    k = seed * 13
    while x < c.wm - 0.02:
        c.rune(x, (y0 + y1) / 2, (y1 - y0) * 0.6, k, gold, w=0.0025)
        x += (y1 - y0) * 0.75
        k += 1


def milia_robe(w=2048, h=1024):
    purple, green, gold = (0.44, 0.23, 0.62), (0.16, 0.42, 0.34), GOLD
    c = Canvas(w, h, 1.85, 0.98, purple)
    rng = np.random.default_rng(7)
    c.folds(24, (0.22, 0.1, 0.32), rng, a=0.3)
    milia_band_runes(c, 0.86, 0.96, green, gold, 2)
    return c


def milia_cape(w=1152, h=2048):
    """ミリアのマント：紫地、すそと左右に緑の帯（金のルーン）、月と星"""
    purple, green, gold = (0.4, 0.21, 0.58), (0.16, 0.42, 0.34), GOLD
    c = Canvas(w, h, 0.68, 1.24, purple)
    rng = np.random.default_rng(9)
    c.folds(12, (0.2, 0.09, 0.3), rng, a=0.3)
    milia_band_runes(c, 1.12, 1.22, green, gold, 3)
    for x0, x1 in ((0.0, 0.06), (0.62, 0.68)):
        c.vband(x0, x1, green, edge=(0.06, 0.16, 0.12))
    for (x, y, kind) in ((0.15, 0.95, 'm'), (0.33, 1.02, 's'), (0.5, 0.93, 'm'), (0.24, 0.8, 's'), (0.45, 0.78, 's')):
        if kind == 's':
            c.star(x, y, 0.025, gold, outline=(0.3, 0.2, 0.1), ow=0.003)
        else:
            c.moon(x, y, 0.03, gold, purple)
    return c


def milia_tabard(w=512, h=2048):
    """ミリアの前掛け：緑地に金の星座、下に金の円の紋様"""
    green, gold, dark = (0.18, 0.44, 0.36), GOLD, (0.06, 0.16, 0.12)
    c = Canvas(w, h, 0.22, 0.88, green)
    stars = [(0.06, 0.12), (0.11, 0.08), (0.16, 0.14), (0.13, 0.22), (0.07, 0.27), (0.15, 0.32)]
    c.line(stars, 0.0016, gold, 0.9)
    for (x, y) in stars:
        c.star(x, y, 0.01, gold)
    cy = 0.66
    # 魔法陣：二重の輪のあいだにルーン、中に六芒星
    c.disc(0.11, cy, 0.072, gold)
    c.disc(0.11, cy, 0.066, green)
    c.disc(0.11, cy, 0.046, gold)
    c.disc(0.11, cy, 0.042, green)
    for k in range(8):
        ang = k / 8 * math.tau
        c.rune(0.11 + math.cos(ang) * 0.056, cy + math.sin(ang) * 0.056, 0.012, k + 3, gold, w=0.0016)
    for rot in (0.0, math.pi):
        tri = [(0.11 + math.cos(rot + math.pi / 2 + t * math.tau / 3) * 0.04, cy + math.sin(rot + math.pi / 2 + t * math.tau / 3) * 0.04) for t in range(4)]
        c.line(tri, 0.0022, gold)
    c.star(0.11, cy, 0.012, gold)
    c.line([(0.0, 0.8), (0.11, 0.86), (0.22, 0.8)], 0.004, gold)
    c.rect(0, 0, 0.012, 0.88, dark)
    c.rect(0.208, 0, 0.22, 0.88, dark)
    return c


if __name__ == '__main__':
    import sys
    out = sys.argv[1]
    for f in (serena_overskirt, serena_tabard, milia_robe, milia_cape, milia_tabard):
        f().save_png(f"{out}/pat_{f.__name__}.png")
        print('wrote', f.__name__)
