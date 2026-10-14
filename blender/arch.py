# -*- coding: utf-8 -*-
"""
ひかりの伝説 — 建物の部品（作り込んだ木組みの家など）

ローカル座標：Blender の x = 幅, y = 奥行き（正面は -y ＝ ゲームの +Z）, z = 上
"""
import math, random
from mathutils import Vector
from bkit import MB, mat


class Offset:
    """MB への追加を平行移動するラッパー（gable_roof などをローカル原点以外に置く）"""
    def __init__(self, mb, off):
        self.mb, self.off = mb, Vector(off)

    def poly(self, verts, faces, m, **kw):
        self.mb.poly([tuple(Vector(v) + self.off) for v in verts], faces, m, **kw)

    def add(self, kind, m, loc=(0, 0, 0), **kw):
        self.mb.add(kind, m, loc=tuple(Vector(loc) + self.off), **kw)


# ---------------------------------------------------------------- 向きのある箱
def obox(mb, m, c, ax, ay, az, hx, hy, hz):
    """中心 c、直交する軸 ax/ay/az、半分の寸法 hx/hy/hz の箱"""
    c, ax, ay, az = Vector(c), Vector(ax), Vector(ay), Vector(az)
    vs = []
    for sz in (-1, 1):
        for sy in (-1, 1):
            for sx in (-1, 1):
                vs.append(tuple(c + ax * sx * hx + ay * sy * hy + az * sz * hz))
    # 0:(-,-,-) 1:(+,-,-) 2:(-,+,-) 3:(+,+,-) 4..7 = 上
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    if ax.cross(ay).dot(az) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    mb.poly(vs, faces, m)


def beam(mb, m, a, b, n, t=0.2, depth=0.1, back=0.04):
    """壁面（法線 n）の上で a→b を結ぶ角材。壁から depth だけ出る"""
    a, b, n = Vector(a), Vector(b), Vector(n).normalized()
    d = b - a
    L = d.length
    if L < 1e-4:
        return
    d /= L
    s = n.cross(d).normalized()
    c = (a + b) / 2 + n * (depth - back) / 2
    obox(mb, m, c, d, s, n, L / 2, t / 2, (depth + back) / 2)


# ---------------------------------------------------------------- 壁面の定義
def faces_of(w, d):
    """外から見て：原点（左下）、右向き u、外向き法線 n、長さ L"""
    return {
        'front': (Vector((-w / 2, -d / 2, 0)), Vector((1, 0, 0)), Vector((0, -1, 0)), w),
        'back': (Vector((w / 2, d / 2, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), w),
        'left': (Vector((-w / 2, d / 2, 0)), Vector((0, -1, 0)), Vector((-1, 0, 0)), d),
        'right': (Vector((w / 2, -d / 2, 0)), Vector((0, 1, 0)), Vector((1, 0, 0)), d),
    }


class HouseMats:
    def __init__(self, roof, shutter):
        self.stone = mat("StoneDark", (0.52, 0.50, 0.48), 0.9)
        self.plaster = mat("Plaster", (0.86, 0.82, 0.72), 0.9)
        self.timber = mat("WoodDark", (0.25, 0.15, 0.08), 0.8)
        self.wood = mat("Wood", (0.42, 0.27, 0.14), 0.8)
        self.door = mat("Door", (0.30, 0.19, 0.11), 0.85)
        self.iron = mat("Iron", (0.12, 0.12, 0.13), 0.5, 0.8)
        self.glass = mat("WindowLight", (0.05, 0.06, 0.07), 0.12, emit=(1.0, 0.72, 0.38), emit_strength=2.0)
        self.roof = roof
        self.shutter = shutter
        self.gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)


def window(mb, M, o, u, n, cx, z0, ww, wh, shutters=True, box=None, flowers=None, rnd=None):
    """壁面に窓：枠・ガラス・十字の桟・窓台・よろい戸・花箱"""
    p = lambda x, z, out=0.0: o + u * x + Vector((0, 0, z)) + n * out
    up = Vector((0, 0, 1))
    x0, x1, z1 = cx - ww / 2, cx + ww / 2, z0 + wh
    # ガラス（壁の少し前）
    obox(mb, M.glass, p(cx, z0 + wh / 2, 0.015), u, up, n, ww / 2, wh / 2, 0.012)
    # 枠
    ft = 0.12
    beam(mb, M.timber, p(x0 - ft / 2, z0 - ft), p(x0 - ft / 2, z1 + ft), n, ft, 0.11)
    beam(mb, M.timber, p(x1 + ft / 2, z0 - ft), p(x1 + ft / 2, z1 + ft), n, ft, 0.11)
    beam(mb, M.timber, p(x0 - ft, z1 + ft / 2), p(x1 + ft, z1 + ft / 2), n, ft * 1.4, 0.12)
    # 桟
    beam(mb, M.timber, p(cx, z0), p(cx, z1), n, 0.045, 0.05)
    beam(mb, M.timber, p(x0, z0 + wh * 0.58), p(x1, z0 + wh * 0.58), n, 0.045, 0.05)
    # 窓台
    obox(mb, M.wood, p(cx, z0 - ft - 0.03, 0.09), u, up, n, ww / 2 + 0.2, 0.05, 0.13)
    # よろい戸（開いて壁にそって）
    if shutters:
        sw = ww / 2 + 0.04
        for side in (-1, 1):
            sx = cx + side * (ww / 2 + ft + sw / 2 + 0.02)
            boards = 3
            for k in range(boards):
                bx = sx - sw / 2 + (k + 0.5) * sw / boards
                obox(mb, M.shutter, p(bx, z0 + wh / 2, 0.045), u, up, n, sw / boards / 2 - 0.008, wh / 2 + 0.06, 0.025)
            for zz in (z0 + 0.18, z1 - 0.18):
                obox(mb, M.shutter, p(sx, zz, 0.08), u, up, n, sw / 2, 0.05, 0.012)
                # 蝶番
                obox(mb, M.iron, p(sx - side * sw * 0.2, zz, 0.095), u, up, n, sw * 0.3, 0.022, 0.006)
    if box:
        bz = z0 - ft - 0.28
        obox(mb, M.wood, p(cx, bz, 0.2), u, up, n, ww / 2 + 0.12, 0.13, 0.17)
        if flowers and rnd:
            leaf = mat("Hedge", (0.2, 0.45, 0.16), 0.9)
            mb.add('ico', leaf, loc=tuple(p(cx, bz + 0.17, 0.2)), r=0.5, sub=2, scale=((ww + 0.2) / 1.0, 0.34, 0.22), jitter=0.04, seed=int(cx * 10))
            for k in range(9):
                fx = cx - ww / 2 + (k + 0.5) * ww / 9 + rnd.uniform(-0.04, 0.04)
                mb.add('ico', flowers[(k + int(cx * 3)) % len(flowers)], loc=tuple(p(fx, bz + 0.27 + rnd.uniform(0, 0.08), 0.2 + rnd.uniform(-0.08, 0.08))), r=0.065, sub=1)


def door(mb, M, o, u, n, cx, z0, dw=1.3, dh=2.3, canopy=True):
    p = lambda x, z, out=0.0: o + u * x + Vector((0, 0, z)) + n * out
    up = Vector((0, 0, 1))
    # 板戸
    planks = 5
    for k in range(planks):
        bx = cx - dw / 2 + (k + 0.5) * dw / planks
        obox(mb, M.door, p(bx, z0 + dh / 2, 0.02), u, up, n, dw / planks / 2 - 0.01, dh / 2, 0.04)
    for zz in (z0 + 0.35, z0 + dh - 0.4):
        obox(mb, M.iron, p(cx - dw * 0.12, zz, 0.07), u, up, n, dw * 0.38, 0.035, 0.012)
    obox(mb, M.door, p(cx, z0 + dh * 0.5, 0.065), u, up, n, dw / 2 - 0.05, 0.06, 0.015)
    mb.add('cyl', M.iron, loc=tuple(p(cx + dw * 0.3, z0 + 1.05, 0.1)), rot=(math.pi / 2, 0, math.atan2(n.y, n.x) + math.pi / 2), r1=0.07, r2=0.07, depth=0.02, seg=12)
    # 枠（太い柱とまぐさ）
    ft = 0.2
    beam(mb, M.timber, p(cx - dw / 2 - ft / 2, z0), p(cx - dw / 2 - ft / 2, z0 + dh + ft), n, ft, 0.14)
    beam(mb, M.timber, p(cx + dw / 2 + ft / 2, z0), p(cx + dw / 2 + ft / 2, z0 + dh + ft), n, ft, 0.14)
    beam(mb, M.timber, p(cx - dw / 2 - ft - 0.15, z0 + dh + ft * 0.6), p(cx + dw / 2 + ft + 0.15, z0 + dh + ft * 0.6), n, ft * 1.5, 0.16)
    # 石段
    mb.add('cube', M.stone, loc=tuple(p(cx, z0 - 0.12, 0.38)), rot=(0, 0, math.atan2(u.y, u.x)), scale=(dw + 0.9, 0.75, 0.26), bevel=0.04)
    mb.add('cube', M.stone, loc=tuple(p(cx, z0 - 0.38, 0.8)), rot=(0, 0, math.atan2(u.y, u.x)), scale=(dw + 1.3, 0.75, 0.26), bevel=0.04)
    if canopy:
        cz = z0 + dh + 0.55
        for side in (-1, 1):
            a = p(cx + side * (dw / 2 + 0.25), cz - 0.5, 0.0)
            b = p(cx + side * (dw / 2 + 0.25), cz - 0.05, 0.75)
            obox(mb, M.timber, (a + b) / 2, u, (b - a).normalized(), u.cross((b - a).normalized()).normalized(), 0.06, (b - a).length / 2, 0.06)
        # 小屋根（前に下がる）
        a = p(cx, cz + 0.15, -0.05)
        b = p(cx, cz - 0.25, 1.0)
        dvec = (b - a).normalized()
        nn = u.cross(dvec)
        if nn.z < 0:
            nn = -nn
        obox(mb, M.roof, (a + b) / 2, u, dvec, nn, dw / 2 + 0.55, (b - a).length / 2 + 0.05, 0.06)


def gable_roof(mb, M, w, d, h, y0, over_x=0.7, over_y=0.55, t=0.22):
    """x 方向に棟がある切妻屋根。厚み・破風板・棟・鼻隠しつき"""
    w2, d2 = w / 2 + over_x, d / 2 + over_y
    drop = over_y * h / (d / 2)          # 軒を出したぶん下げる
    for side in (-1, 1):
        a = Vector((-w2, side * d2, y0 - drop))
        b = Vector((w2, side * d2, y0 - drop))
        c = Vector((w2, 0, y0 + h))
        dd = Vector((-w2, 0, y0 + h))
        slope_n = (b - a).cross(c - b).normalized()
        if slope_n.z < 0:
            slope_n = -slope_n
        dn = slope_n * t
        verts = [a, b, c, dd, a - dn, b - dn, c - dn, dd - dn]
        verts = [tuple(v) for v in verts]
        faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]
        if side > 0:
            faces = [tuple(reversed(f)) for f in faces]
        mb.poly(verts, faces, M.roof)
        # 鼻隠し（軒先の板）
        obox(mb, M.timber, (a + b) / 2 - slope_n * (t + 0.05), Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, side, 0)), w2, 0.1, 0.04)
        # 破風板（妻側の斜めの板）
        for sx in (-1, 1):
            e0 = Vector((sx * (w2 + 0.04), side * d2, y0 - drop - 0.04))
            e1 = Vector((sx * (w2 + 0.04), 0, y0 + h + 0.02))
            dv = (e1 - e0).normalized()
            obox(mb, M.timber, (e0 + e1) / 2 - slope_n * 0.08, dv, Vector((sx, 0, 0)), dv.cross(Vector((sx, 0, 0))).normalized() * (1 if dv.cross(Vector((sx, 0, 0))).z >= 0 else -1),
                 (e1 - e0).length / 2 + 0.05, 0.04, 0.16)
    # 棟がわら
    mb.add('cyl', M.roof, loc=(0, 0, y0 + h + 0.04), rot=(0, math.pi / 2, 0), r1=0.17, r2=0.17, depth=w2 * 2 + 0.1, seg=12)


def half_timber_band(mb, M, face, z0, z1, openings, rnd, braces=True, posts_only=False):
    """壁の 1 段ぶんの木組み：土台・桁・柱・間柱・筋かい"""
    o, u, n, L = face
    p = lambda x, z: o + u * x + Vector((0, 0, z))
    t = 0.22
    beam(mb, M.timber, p(-0.08, z0 + t / 2), p(L + 0.08, z0 + t / 2), n, t, 0.09)
    beam(mb, M.timber, p(-0.08, z1 - t / 2), p(L + 0.08, z1 - t / 2), n, t, 0.09)
    xs = [t / 2, L - t / 2]
    for (cx, oz, ow, oh, kind) in openings:
        if oz < z1 and oz + oh > z0:
            xs += [cx - ow / 2 - 0.32, cx + ow / 2 + 0.32]
    if not posts_only:
        k = 1.6
        x = k
        while x < L - k * 0.6:
            if all(abs(x - xx) > 0.75 for xx in xs) and not any(abs(x - cx) < ow / 2 + 0.4 and oz < z1 and oz + oh > z0 for (cx, oz, ow, oh, kind) in openings):
                xs.append(x)
            x += k
    xs = sorted(set(round(v, 3) for v in xs if 0 <= v <= L))
    for x in xs:
        beam(mb, M.timber, p(x, z0 + t), p(x, z1 - t), n, t * 0.9, 0.08)
    if not braces:
        return
    # 筋かい：開口のない区画に斜め材（左右対称になるように向きを決める）
    for i in range(len(xs) - 1):
        a, b = xs[i], xs[i + 1]
        if b - a < 0.8:
            continue
        if any(oz < z1 and oz + oh > z0 and cx + ow / 2 > a and cx - ow / 2 < b for (cx, oz, ow, oh, kind) in openings):
            continue
        mid = (a + b) / 2
        if mid < L / 2:
            beam(mb, M.timber, p(a + 0.1, z0 + t), p(b - 0.1, z1 - t), n, t * 0.8, 0.07)
        else:
            beam(mb, M.timber, p(a + 0.1, z1 - t), p(b - 0.1, z0 + t), n, t * 0.8, 0.07)
        if b - a > 1.4 and rnd.random() < 0.5:
            beam(mb, M.timber, p(a + 0.1, z0 + (z1 - z0) * 0.5), p(b - 0.1, z0 + (z1 - z0) * 0.5), n, t * 0.6, 0.065)


def build_house_mesh(w, d, wh, roof_m, shutter_m, inn=False, shop=False, seed=1, sign_m=None, flowers=None):
    """作り込んだ 2 階建ての木組みの家（MB を返す）。戻り値：mb, 情報 dict"""
    rnd = random.Random(seed)
    M = HouseMats(roof_m, shutter_m)
    mb = MB()
    PL = 0.6                     # 石の土台の高さ
    g = max(2.6, wh * 0.72)      # 1 階
    up = max(2.4, wh * 0.62)     # 2 階
    J = 0.45                     # 2 階の張り出し（前と後ろ）
    z_top = PL + g + up
    # 石の土台（地面にめり込ませて坂でも浮かない）
    mb.add('cube', M.stone, loc=(0, 0, PL / 2 - 0.7), scale=(w + 0.3, d + 0.3, PL + 1.4), bevel=0.06)
    # 1 階・2 階の壁
    obox(mb, M.plaster, (0, 0, PL + g / 2), (1, 0, 0), (0, 1, 0), (0, 0, 1), w / 2, d / 2, g / 2)
    obox(mb, M.plaster, (0, 0, PL + g + up / 2), (1, 0, 0), (0, 1, 0), (0, 0, 1), w / 2, d / 2 + J, up / 2)
    # 床の梁（張り出しの下に梁の端が並ぶ）
    for side in (-1, 1):
        nb = int(w / 0.55)
        for k in range(nb + 1):
            x = -w / 2 + 0.1 + k * (w - 0.2) / nb
            obox(mb, M.timber, (x, side * (d / 2 + J / 2), PL + g - 0.1), (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.08, J / 2 + 0.06, 0.1)
        obox(mb, M.timber, (0, side * (d / 2 + J + 0.02), PL + g + 0.06), (1, 0, 0), (0, 1, 0), (0, 0, 1), w / 2 + 0.08, 0.08, 0.14)
    F1 = faces_of(w, d)
    F2 = faces_of(w, d + 2 * J)
    # 開口部の配置
    ops1 = {k: [] for k in F1}
    ops2 = {k: [] for k in F1}
    fw = F1['front'][3]
    door_x = fw / 2
    ops1['front'].append((door_x, PL, 1.3, 2.3, 'door'))
    ww1, wh1 = 0.95, 1.15
    for cx in (fw * 0.2, fw * 0.8):
        if abs(cx - door_x) > 1.6:
            ops1['front'].append((cx, PL + 0.95, ww1, wh1, 'win'))
    nwin = max(2, int(w / 2.6))
    for k in range(nwin):
        cx = fw * (k + 0.5) / nwin
        ops2['front'].append((cx, PL + g + 0.75, 0.85, 1.05, 'win'))
        ops2['back'].append((cx, PL + g + 0.75, 0.85, 1.05, 'win'))
    for k in range(max(1, int(w / 3.6))):
        cx = fw * (k + 0.5) / max(1, int(w / 3.6))
        ops1['back'].append((cx, PL + 0.95, ww1, wh1, 'win'))
    for side in ('left', 'right'):
        L1 = F1[side][3]
        ops1[side].append((L1 / 2, PL + 0.95, ww1, wh1, 'win'))
        L2 = F2[side][3]
        ops2[side].append((L2 / 2, PL + g + 0.75, 0.8, 1.0, 'win'))
    # 木組み
    for k, face in F1.items():
        half_timber_band(mb, M, face, PL, PL + g, ops1[k], rnd, braces=False)
    for k, face in F2.items():
        half_timber_band(mb, M, face, PL + g, z_top, ops2[k], rnd, braces=True)
    # 窓と扉
    for k, face in F1.items():
        o, u, n, L = face
        for (cx, oz, ow, oh, kind) in ops1[k]:
            if kind == 'door':
                door(mb, M, o, u, n, cx, oz, ow, oh)
            else:
                window(mb, M, o, u, n, cx, oz, ow, oh, shutters=True, box=(k == 'front'), flowers=flowers, rnd=rnd)
    for k, face in F2.items():
        o, u, n, L = face
        for (cx, oz, ow, oh, kind) in ops2[k]:
            window(mb, M, o, u, n, cx, oz, ow, oh, shutters=(k in ('front', 'back')), box=False)
    # 張り出しを支える方杖（角と中央）
    for side in (-1, 1):
        for x in (-w / 2 + 0.15, w / 2 - 0.15):
            a = Vector((x, side * (d / 2 + 0.02), PL + g - 0.95))
            b = Vector((x, side * (d / 2 + J - 0.05), PL + g - 0.12))
            dv = (b - a).normalized()
            obox(mb, M.timber, (a + b) / 2, dv, (1, 0, 0), dv.cross(Vector((1, 0, 0))), (b - a).length / 2, 0.08, 0.08)
    # 妻壁（三角）と木組み
    rh = 2.4 + (d + 2 * J) * 0.16
    D2 = d / 2 + J
    for sx in (-1, 1):
        x = sx * w / 2
        RL = 0.3   # 屋根は壁の上の梁が突き抜けないよう少し上げる
        tri = [(x, -D2, z_top), (x, D2, z_top), (x, D2, z_top + RL - 0.24), (x, 0, z_top + RL + rh - 0.25), (x, -D2, z_top + RL - 0.24)]
        mb.poly(tri, [(0, 1, 2, 3, 4) if sx > 0 else (4, 3, 2, 1, 0)], M.plaster)
        n = Vector((sx, 0, 0))
        beam(mb, M.timber, (x, 0, z_top), (x, 0, z_top + RL + rh - 0.45), n, 0.22, 0.08)
        beam(mb, M.timber, (x, -D2 * 0.52, z_top + rh * 0.48), (x, D2 * 0.52, z_top + rh * 0.48), n, 0.2, 0.08)
        for sy in (-1, 1):
            beam(mb, M.timber, (x, sy * D2 * 0.95, z_top + 0.1), (x, sy * D2 * 0.4, z_top + rh * 0.48), n, 0.18, 0.07)
        # 屋根裏の小窓
        window(mb, M, Vector((x, 0, 0)), Vector((0, sx, 0)), n, 0.0, z_top + rh * 0.5, 0.5, 0.6, shutters=False)
    gable_roof(mb, M, w, d + 2 * J, rh, z_top + 0.3)
    # 煙突（石積み、笠石と煙突つぼ）
    chx, chy = w * 0.27, d * 0.18
    ch_top = z_top + 0.3 + rh * (1 - chy / D2) + 1.3
    mb.add('cube', M.stone, loc=(chx, chy, (z_top + ch_top) / 2), scale=(0.8, 0.8, ch_top - z_top), bevel=0.05)
    mb.add('cube', M.stone, loc=(chx, chy, ch_top + 0.08), scale=(1.0, 1.0, 0.16), bevel=0.04)
    for k in (-1, 1):
        mb.add('cyl', mat("ClayPot", (0.6, 0.32, 0.2), 0.8), loc=(chx + k * 0.18, chy, ch_top + 0.36), r1=0.13, r2=0.1, depth=0.42, seg=12)
    # 戸口の横のランタン
    lx = door_x - w / 2 + 1.25
    mb.add('cube', M.iron, loc=(lx, -d / 2 - 0.25, PL + 2.25), scale=(0.05, 0.5, 0.05))
    mb.add('cube', M.glass, loc=(lx, -d / 2 - 0.45, PL + 1.98), scale=(0.2, 0.2, 0.28), bevel=0.02)
    mb.add('cyl', M.iron, loc=(lx, -d / 2 - 0.45, PL + 2.2), r1=0.19, r2=0.02, depth=0.16, seg=4)
    # 看板（宿屋・店）
    if (inn or shop) and sign_m is not None:
        sx_ = -w / 2 + 1.0 if w > 9 else w / 2 - 0.9
        sx_ = door_x - w / 2 + 2.3
        mb.add('cube', M.iron, loc=(sx_, -d / 2 - J - 0.6, PL + g - 0.35), scale=(0.05, 1.2, 0.05))
        mb.add('cube', M.iron, loc=(sx_, -d / 2 - J - 0.25, PL + g - 0.6), rot=(math.radians(-45), 0, 0), scale=(0.04, 0.04, 0.7))
        mb.add('cube', sign_m, loc=(sx_, -d / 2 - J - 0.85, PL + g - 0.95), rot=(0, 0, math.pi / 2), scale=(0.08, 1.0, 0.7), bevel=0.02)
        for k in (-1, 1):
            mb.add('cube', M.iron, loc=(sx_, -d / 2 - J - 0.85 + k * 0.35, PL + g - 0.48), scale=(0.015, 0.015, 0.25))
        if inn:
            mb.add('sphere', mat("BannerRed", (0.75, 0.10, 0.10), 0.7, double=True), loc=(sx_ - 0.06, -d / 2 - J - 0.85, PL + g - 0.95), r=0.17, seg=12, rings=8, scale=(0.4, 1, 1))
        else:
            mb.add('cube', M.gold, loc=(sx_ - 0.06, -d / 2 - J - 0.85, PL + g - 0.95), rot=(math.pi / 4, 0, 0), scale=(0.04, 0.36, 0.36))
    info = {'top': z_top + 0.3 + rh, 'chimney': (chx, chy, ch_top + 0.6), 'depth': d + 2 * J}
    return mb, info


def arch_wall(mb, m, cx, cy, w, z0, z1, r, thick, seg=20):
    """アーチ形にくりぬいた壁（x 方向に幅 w、y 方向に厚さ thick、z0 がアーチの起点、半径 r）"""
    out = [(-w / 2, z0), (-r, z0)]
    for k in range(seg + 1):
        a = math.pi * (1 - k / seg)
        out.append((math.cos(a) * r, z0 + math.sin(a) * r))
    out += [(r, z0), (w / 2, z0), (w / 2, z1), (-w / 2, z1)]
    # 重複点をのぞく
    pts = []
    for p in out:
        if not pts or (abs(p[0] - pts[-1][0]) > 1e-5 or abs(p[1] - pts[-1][1]) > 1e-5):
            pts.append(p)
    n = len(pts)
    verts = [(cx + x, cy - thick / 2, z) for x, z in pts] + [(cx + x, cy + thick / 2, z) for x, z in pts]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, n + i, n + j, j))
    # 向きをそろえる：前面（-y）の法線が -y を向くように
    mb.poly(verts, faces, m)
