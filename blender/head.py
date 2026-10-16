# -*- coding: utf-8 -*-
"""
ひかりの伝説 — 頭（一から作る顔）

横顔の輪郭の表（高さ・幅・前の奥行き・後ろの奥行き）から輪切りの形をつくり、細かい網目でつないで頭にする。
そのうえに 鼻・目のくぼみ・眉の盛り上がり・ほお・口・あご先 を「形」として足す（彫刻のように）。
座標：頭の中心からの位置（m）。x = キャラの左, y = 後ろ（前は -y）, z = 上
"""
import math
import bpy, bmesh
from mathutils import Vector

# 輪郭の表：(z, 横の半幅 W, 前の奥行き Df, 後ろの奥行き Db, 中心の前後ずれ yc)
ROWS_F = [
    (0.118, 0.0, 0.0, 0.0, 0.0),
    (0.114, 0.03, 0.03, 0.034, 0.0),
    (0.104, 0.058, 0.058, 0.066, 0.0),
    (0.085, 0.08, 0.08, 0.09, 0.0),
    (0.058, 0.092, 0.094, 0.104, 0.0),
    (0.028, 0.096, 0.1, 0.11, 0.0),
    (0.004, 0.096, 0.101, 0.109, 0.0),
    (-0.018, 0.093, 0.1, 0.104, 0.0),
    (-0.038, 0.088, 0.098, 0.094, 0.0),
    (-0.056, 0.078, 0.095, 0.08, 0.0),
    (-0.072, 0.064, 0.092, 0.066, 0.0),
    (-0.086, 0.047, 0.087, 0.058, 0.0),
    (-0.098, 0.029, 0.08, 0.054, 0.0),
    (-0.107, 0.016, 0.07, 0.052, 0.0),
    (-0.111, 0.024, 0.052, 0.052, 0.008),
    (-0.113, 0.036, 0.04, 0.05, 0.014),
    (-0.124, 0.042, 0.036, 0.047, 0.016),
    (-0.15, 0.043, 0.036, 0.046, 0.016),
    (-0.2, 0.046, 0.038, 0.048, 0.016),
    (-0.24, 0.05, 0.04, 0.05, 0.016),
]
# 男性：あごがしっかり、横幅がやや広い
ROWS_M = [
    (0.118, 0.0, 0.0, 0.0, 0.0),
    (0.114, 0.031, 0.03, 0.034, 0.0),
    (0.104, 0.06, 0.058, 0.066, 0.0),
    (0.085, 0.083, 0.08, 0.09, 0.0),
    (0.058, 0.095, 0.094, 0.104, 0.0),
    (0.028, 0.099, 0.1, 0.11, 0.0),
    (0.004, 0.099, 0.101, 0.109, 0.0),
    (-0.018, 0.097, 0.1, 0.104, 0.0),
    (-0.038, 0.093, 0.099, 0.094, 0.0),
    (-0.056, 0.086, 0.097, 0.082, 0.0),
    (-0.072, 0.075, 0.094, 0.07, 0.0),
    (-0.086, 0.06, 0.09, 0.062, 0.0),
    (-0.098, 0.04, 0.084, 0.058, 0.0),
    (-0.108, 0.024, 0.075, 0.056, 0.0),
    (-0.113, 0.03, 0.056, 0.054, 0.008),
    (-0.116, 0.042, 0.042, 0.052, 0.014),
    (-0.128, 0.05, 0.04, 0.05, 0.016),
    (-0.15, 0.051, 0.04, 0.05, 0.016),
    (-0.2, 0.053, 0.042, 0.052, 0.016),
    (-0.24, 0.056, 0.044, 0.054, 0.016),
]


def _catmull(rows, t):
    n = len(rows)
    x = t * (n - 1)
    i = min(int(x), n - 2)
    u = x - i
    p0, p1, p2, p3 = rows[max(i - 1, 0)], rows[i], rows[i + 1], rows[min(i + 2, n - 1)]
    out = []
    for a, b, c, d in zip(p0, p1, p2, p3):
        out.append(0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u ** 3))
    return out


def _g(x, s):
    return math.exp(-(x / s) ** 2)


def _sm(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def sculpt(p, fem):
    """顔の形を足す（p: 頭の中心からの位置）"""
    x, y, z = p.x, p.y, p.z
    front = max(0.0, -y) / 0.1
    d = Vector((0, 0, 0))
    if y < 0:
        # 鼻：細い鼻筋 → 小さくとがった鼻先（鳥山明さん風の小さな鼻）
        zb, zt = -0.004, -0.04
        if zt - 0.008 < z < zb + 0.004:
            k = _sm(zb + 0.004, zt, z)
            amt = (0.002 + (0.011 if fem else 0.014) * k ** 1.6) * _sm(zt - 0.008, zt - 0.001, z)
            sx = 0.0045 + 0.0045 * k
            d.y -= amt * _g(x, sx)
        # 小鼻（鼻の左右）
        for s_ in (-1, 1):
            d.y -= 0.0022 * _g(x - s_ * 0.0085, 0.004) * _g(z + 0.038, 0.004)
        # 目のまわり：ゆるいくぼみ、眉の下で少し深い
        for s_ in (-1, 1):
            d.y += 0.004 * _g(x - s_ * 0.041, 0.022) * _g(z + 0.016, 0.014) * front
        # 眉の盛り上がり
        d.y -= (0.0018 if fem else 0.003) * _g(z - 0.016, 0.008) * _sm(0.075, 0.03, abs(x)) * front
        # ほお（ふっくら）
        for s_ in (-1, 1):
            d += Vector((s_ * 0.002, -0.0035, 0)) * _g(x - s_ * 0.052, 0.018) * _g(z + 0.05, 0.016) * (1.3 if fem else 1.0)
        # 上くちびる・口のくぼみ・下くちびる
        d.y -= 0.0018 * _g(x, 0.016) * _g(z + 0.062, 0.005)
        d.y += 0.0012 * _g(x, 0.014) * _g(z + 0.069, 0.0025)
        d.y -= 0.0014 * _g(x, 0.012) * _g(z + 0.075, 0.004)
        # あご先を少し前へ
        d.y -= 0.004 * _g(x, 0.014) * _g(z + 0.1, 0.008)
    return p + d


def build_head(cfg, name, coll, pivot, rig_fn):
    hs = cfg.get('head_scale', 0.98)
    fem = cfg.get('build') == 'female'
    rows = ROWS_F if fem else ROWS_M
    center = pivot + (Vector((0, 0.0, 1.615)) - pivot) * hs
    nr, seg = 120, 96
    bm = bmesh.new()
    rings = []
    uvs = {}
    FW, FH = 0.22, 0.26       # face.py の顔の絵の範囲と同じ

    def uv_of(p):
        # 顔の前は正面から投影、後ろは何も描いていない左右の端（肌の色）を使う
        u = 0.5 + p.x / FW
        if p.y > -0.01:
            u = 0.5 + (0.49 if p.x >= 0 else -0.49)
        return (min(max(u, 0.005), 0.995), min(max(0.5 + p.z / FH, 0.005), 0.995))
    for i in range(nr + 1):
        t = i / nr
        z, W, Df, Db, yc = _catmull(rows, t)
        ring = []
        if W < 1e-4:
            ring = [bm.verts.new(center + Vector((0, 0, z)) * hs)]
            uvs[ring[0]] = uv_of(Vector((0, 1, z)))
            rings.append(ring)
            continue
        for k in range(seg):
            a = k / seg * math.tau
            c, s = math.cos(a), math.sin(a)
            x = s * W
            if c > 0:
                y = -(c ** 0.8) * Df       # 顔の前はやや平ら
            else:
                y = (-c) * Db
            p = sculpt(Vector((x, y + yc, z)), fem)
            bv = bm.verts.new(center + p * hs)
            uvs[bv] = uv_of(p)
            ring.append(bv)
        rings.append(ring)
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        if len(r0) == 1:
            for k in range(seg):
                bm.faces.new([r0[0], r1[k], r1[(k + 1) % seg]])
            continue
        for k in range(seg):
            bm.faces.new([r0[k], r1[k], r1[(k + 1) % seg], r0[(k + 1) % seg]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        f.smooth = True
        for lp in f.loops:
            lp[uvl].uv = uvs[lp.vert]
    me = bpy.data.meshes.new(name + "_Head")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name + "_Head", me)
    coll.objects.link(ob)
    # 耳
    ears = bmesh.new()
    for s_ in (-1, 1):
        zc = -0.018
        z_, W_, Df_, Db_, yc_ = _catmull(rows, 0.39)
        e = center + Vector((s_ * (W_ + 0.004), 0.008, zc)) * hs
        tmp = bmesh.new()
        bmesh.ops.create_uvsphere(tmp, u_segments=20, v_segments=12, radius=1.0)
        for v in tmp.verts:
            co = v.co
            v.co = e + Vector((co.x * 0.008 * hs, co.y * 0.018 * hs, co.z * 0.03 * hs))
            # 外側の縁をそらせ、内側をくぼませる
            if co.x * s_ > 0:
                v.co.x += s_ * 0.004 * hs * (1 - co.y ** 2)
        vm = {v: ears.verts.new(v.co) for v in tmp.verts}
        for f in tmp.faces:
            ears.faces.new([vm[v] for v in f.verts]).smooth = True
        tmp.free()
    eme = bpy.data.meshes.new(name + "_Ears")
    ears.to_mesh(eme)
    ears.free()
    eob = bpy.data.objects.new(name + "_Ears", eme)
    coll.objects.link(eob)
    rig_fn(ob, center, hs)
    rig_fn(eob, center, hs)
    return ob, eob, me
