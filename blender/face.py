# -*- coding: utf-8 -*-
"""
ひかりの伝説 — キャラの顔（描いた目・まつ毛の線・眉・口・ほお紅）

目は「顔の表面に沿わせた薄い板」に、Python で描いた目の絵（白目・虹彩・瞳孔・光・上まぶたの影）を貼る。
まつ毛の線・二重の線・眉・口は細いチューブで立体にする。
"""
import math
import bpy, bmesh
import numpy as np
from mathutils import Vector
from bkit import principled


# ---------------------------------------------------------------- 目の形（テクスチャと立体で共通）
def _st(st):
    if st is True:
        return 'fem'
    if st is False or st is None:
        return 'male'
    return st


def lid_top(a, st):
    """a = 0（目頭）..1（目じり）での上まぶたの高さ（0..1、目の板の中）。st: male / fem / cool / cute"""
    st = _st(st)
    a = min(max(a, 0.0), 1.0)
    k = math.sin(math.pi * a)
    if st == 'cool':        # きりっと：上まぶたは平たく、目じりが上がる
        v = 0.5 + 0.34 * (k ** 0.55) + 0.12 * a
    elif st == 'cute':      # まるく大きい
        v = 0.5 + 0.46 * (k ** 0.62) + 0.03 * a
    else:
        v = 0.5 + 0.43 * (k ** 0.75) + (0.05 if st == 'fem' else 0.02) * a
    return v - (0.12 if a < 0.08 else 0.0) * (1 - a / 0.08)


def lid_bot(a, st):
    st = _st(st)
    a = min(max(a, 0.0), 1.0)
    k = math.sin(math.pi * a)
    if st == 'cool':
        return 0.5 - 0.26 * (k ** 1.1) + 0.13 * a
    if st == 'cute':
        return 0.5 - 0.37 * (k ** 1.0) + 0.04 * a
    return 0.5 - 0.33 * (k ** 1.1) + 0.06 * a


IRIS_C = (0.5, 0.47)        # 虹彩の中心（板の中）
IRIS_R = (0.27, 0.33)       # 横・縦の半径


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def eye_image(name, iris_rgb, fem, size=512):
    """目の絵（RGBA）。行は下から上（Blender の pixels の並び）"""
    st = _st(fem)
    IR = {'cool': (0.24, 0.31), 'cute': (0.29, 0.35)}.get(st, IRIS_R)
    n = size
    v, u = np.mgrid[0:n, 0:n] / (n - 1)          # u: 目頭→目じり, v: 下→上
    top = np.vectorize(lambda a: lid_top(a, fem))(u[0])[None, :]
    bot = np.vectorize(lambda a: lid_bot(a, fem))(u[0])[None, :]
    aa = 1.5 / n
    inside = _smooth(-aa, aa, top - v) * _smooth(-aa, aa, v - bot) * _smooth(0.0, 0.03, u) * _smooth(1.0, 0.97, u)
    # 白目：上まぶたの影・目頭目じりのかげり
    sclera = np.ones((n, n, 3)) * np.array([0.97, 0.97, 0.99])
    lid_sh = _smooth(0.22, 0.0, top - v)
    corner = _smooth(0.25, 0.0, np.minimum(u, 1 - u))
    sclera *= (1 - lid_sh[..., None] * np.array([0.42, 0.40, 0.32]))
    sclera *= (1 - corner[..., None] * np.array([0.18, 0.2, 0.15]))
    # 虹彩
    dx = (u - IRIS_C[0]) / IR[0]
    dy = (v - IRIS_C[1]) / IR[1]
    r = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)
    iris_m = _smooth(1.0 + aa * 4, 1.0 - aa * 4, r)
    rng = np.random.default_rng(7)
    fib = np.zeros_like(r)
    for k in range(1, 40):
        fib += np.sin(ang * k * 3 + rng.random() * 6.28) * rng.random() / k
    fib = fib / np.abs(fib).max()
    base = np.array(iris_rgb)
    light = np.clip(base * 1.9 + 0.08, 0, 1)
    dark = base * 0.35
    grad = _smooth(-0.9, 0.9, -dy)                     # 下ほど明るい（アニメ調）
    col = dark[None, None, :] * (1 - grad[..., None]) + light[None, None, :] * grad[..., None]
    col *= (0.85 + 0.15 * fib[..., None] * _smooth(0.2, 0.8, r)[..., None])
    ring = _smooth(0.78, 1.0, r)                        # ふちの濃い輪
    col *= (1 - ring[..., None] * 0.65)
    # 上半分に上まぶたの影
    col *= (1 - _smooth(0.35, -0.6, dy)[..., None] * 0.35)
    # 瞳孔
    pr = np.sqrt((dx / 0.42) ** 2 + (dy / 0.46) ** 2)
    pupil = _smooth(1.0 + aa * 10, 1.0 - aa * 10, pr)
    col = col * (1 - pupil[..., None]) + np.array([0.02, 0.02, 0.03]) * pupil[..., None]
    rgb = sclera * (1 - iris_m[..., None]) + col * iris_m[..., None]
    # 光（大きい丸・小さい丸）
    hl = [(IRIS_C[0] - 0.1, IRIS_C[1] + 0.14, 0.075, 1.0), (IRIS_C[0] + 0.1, IRIS_C[1] - 0.16, 0.035, 0.85)]
    if st == 'cute':
        hl += [(IRIS_C[0] - 0.02, IRIS_C[1] + 0.2, 0.03, 0.9), (IRIS_C[0] + 0.12, IRIS_C[1] + 0.05, 0.022, 0.7)]
    for (hx, hy, hr, hk) in hl:
        d = np.sqrt(((u - hx) / hr) ** 2 + ((v - hy) / hr) ** 2)
        h = _smooth(1.0, 0.75, d) * hk * iris_m
        rgb = rgb * (1 - h[..., None]) + h[..., None]
    rgba = np.concatenate([np.clip(rgb, 0, 1), inside[..., None]], -1).astype(np.float32)
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, n, n, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def blush_image(name, size=128):
    n = size
    v, u = np.mgrid[0:n, 0:n] / (n - 1)
    d = np.sqrt(((u - 0.5) / 0.5) ** 2 + ((v - 0.5) / 0.5) ** 2)
    a = _smooth(1.0, 0.0, d) ** 1.5 * 0.35
    rgba = np.stack([np.full_like(a, 1.0), np.full_like(a, 0.45), np.full_like(a, 0.45), a], -1).astype(np.float32)
    img = bpy.data.images.new(name, n, n, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def tex_mat(name, img, rough=0.25, blend=True):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    bsdf = principled(m)
    nt = m.node_tree
    t = next((n for n in nt.nodes if n.type == 'TEX_IMAGE'), None) or nt.nodes.new('ShaderNodeTexImage')
    t.image = img
    nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(t.outputs['Alpha'], bsdf.inputs['Alpha'])
    bsdf.inputs['Roughness'].default_value = rough
    for attr, val in (('blend_method', 'BLEND'), ('surface_render_method', 'BLENDED')):
        try:
            setattr(m, attr, val)
        except Exception:
            pass
    m.use_backface_culling = True
    return m


def patch_coords(surf, P, cx, cz, w, h, s, lift, nu, nv, zfun):
    """surface_patch と同じ順番の頂点位置。zfun(a, b) が板の中の高さ（-0.5..0.5）を返す（まばたき・口の形用）"""
    out = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            a, b = i / nu, j / nv
            x, z = P(cx + s * (a - 0.5) * w, cz + zfun(a, b) * h)
            p, n = surf.front(x, z)
            out.append(p + n * lift)
    return out


def add_shape(ob, name, coords):
    """形のキー（シェイプキー）を足す。coords は頂点と同じ順番"""
    if ob.data.shape_keys is None:
        ob.shape_key_add(name='Basis', from_mix=False)
    k = ob.shape_key_add(name=name, from_mix=False)
    for i, c in enumerate(coords):
        k.data[i].co = c
    return k


def surface_patch(surf, P, cx, cz, w, h, s, m, name, coll, lift=0.0012, nu=16, nv=10):
    """顔の表面に沿った UV つきの板（cx, cz は頭のスケール前の座標）。s = 左右（+1 = キャラの左）"""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    grid = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            a, b = i / nu, j / nv
            x, z = P(cx + s * (a - 0.5) * w, cz + (b - 0.5) * h)
            p, n = surf.front(x, z)
            row.append((bm.verts.new(p + n * lift), (a, b)))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            if s < 0:
                q = list(reversed(q))
            f = bm.faces.new([e[0] for e in q])
            for loop, e in zip(f.loops, q):
                loop[uv].uv = e[1]
            f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


# ================================================================ マンガ風（参考画像のタッチ）の描いた顔
INK = (0.07, 0.045, 0.04)


def _lin(c):
    return np.array([v ** 2.2 for v in c])


def draw_line(rgb, alpha, U, V, pts, widths, col, a=1.0):
    """折れ線をなめらかな太さで塗る（U, V は画素の座標、pts は同じ単位の点列）"""
    col = _lin(col)
    best = np.full(U.shape, 1e9)
    wbest = np.zeros(U.shape)
    for (p0, p1, w0, w1) in zip(pts[:-1], pts[1:], widths[:-1], widths[1:]):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L2 = dx * dx + dy * dy + 1e-12
        t = np.clip(((U - p0[0]) * dx + (V - p0[1]) * dy) / L2, 0, 1)
        px, py = p0[0] + dx * t, p0[1] + dy * t
        d = np.sqrt((U - px) ** 2 + (V - py) ** 2)
        w = w0 + (w1 - w0) * t
        m = d - w * 0.5 < best - wbest * 0.5
        best = np.where(m, d, best)
        wbest = np.where(m, w, wbest)
    px_ = abs(U[0, 1] - U[0, 0]) if U.shape[1] > 1 else 1e-3
    cov = np.clip((wbest * 0.5 - best) / (px_ * 1.2) + 0.5, 0, 1) * a
    rgb[:] = rgb * (1 - cov[..., None]) + col * cov[..., None]
    alpha[:] = np.maximum(alpha, cov)


def manga_lids(st):
    """参考画像の目の形：上まぶたは丸いアーチ、下は平たい（a: 目頭 0 → 目じり 1、値は板の中の高さ）"""
    if st == 'manga_m':
        top = lambda a: 0.48 + 0.3 * math.sin(math.pi * min(max(a, 0), 1)) ** 0.6 + 0.08 * a
        bot = lambda a: 0.4 - 0.18 * math.sin(math.pi * min(max(a, 0), 1)) ** 1.1 + 0.08 * a
    else:
        top = lambda a: 0.5 + 0.34 * math.sin(math.pi * min(max(a, 0), 1)) ** 0.62 + 0.05 * a
        bot = lambda a: 0.38 - 0.22 * math.sin(math.pi * min(max(a, 0), 1)) ** 1.05 + 0.05 * a
    return top, bot


def manga_eye_image(name, iris_rgb, st, size=512):
    """目の絵：白目・大きな黒目（ふちの輪・瞳孔・光）＋太い上まぶたの線・目じりのはね・細い下まぶたの線・二重の線"""
    n = size
    v, u = np.mgrid[0:n, 0:n] / (n - 1)
    top_f, bot_f = manga_lids(st)
    top = np.vectorize(top_f)(u)
    bot = np.vectorize(bot_f)(u)
    aa = 1.5 / n
    inside = _smooth(-aa, aa, top - v) * _smooth(-aa, aa, v - bot) * _smooth(0.0, 0.02, u) * _smooth(1.0, 0.98, u)
    rgb = np.ones((n, n, 3)) * _lin((0.98, 0.98, 1.0))
    rgb *= (1 - _smooth(0.18, 0.0, top - v)[..., None] * np.array([0.3, 0.28, 0.22]))
    # 黒目（上はまぶたに隠れる）
    cx, cy = 0.52, 0.46 if st != 'manga_m' else 0.47
    rx, ry = (0.2, 0.33) if st != 'manga_m' else (0.17, 0.3)
    dx, dy = (u - cx) / rx, (v - cy) / ry
    r = np.sqrt(dx * dx + dy * dy)
    iris = _smooth(1.0 + aa * 6, 1.0 - aa * 6, r)
    base = _lin(iris_rgb)
    light = np.clip(base * 2.2 + 0.03, 0, 1)
    dark = base * 0.25
    grad = _smooth(-0.8, 0.9, -dy)
    col = dark[None, None] * (1 - grad[..., None]) + light[None, None] * grad[..., None]
    col *= (1 - _smooth(0.72, 0.98, r)[..., None] * 0.75)
    pupil = _smooth(0.5 + aa * 8, 0.5 - aa * 8, np.sqrt((dx / 0.95) ** 2 + (dy / 1.05) ** 2))
    col = col * (1 - pupil[..., None]) + _lin((0.03, 0.02, 0.02)) * pupil[..., None]
    rgb = rgb * (1 - iris[..., None]) + col * iris[..., None]
    for (hx, hy, hr) in ((cx - 0.06, cy + 0.12, 0.06), (cx + 0.07, cy - 0.13, 0.028)):
        h = _smooth(hr, hr * 0.7, np.sqrt((u - hx) ** 2 + ((v - hy) * 0.8) ** 2)) * iris
        rgb = rgb * (1 - h[..., None]) + h[..., None]
    alpha = inside.copy()
    # 線（インク）
    a_s = np.linspace(0.0, 1.0, 24)
    thick = [0.035 + 0.05 * math.sin(math.pi * min(a * 1.1, 1.0)) ** 0.5 + 0.03 * a for a in a_s]
    draw_line(rgb, alpha, u, v, [(a, top_f(a) + 0.012) for a in a_s], thick, INK)
    # 目じりのはね
    draw_line(rgb, alpha, u, v, [(0.9, top_f(0.9) + 0.02), (0.99, top_f(1.0) + 0.1)], [0.05, 0.015], INK)
    # 下まぶたの線（目じり側だけ）
    a2 = np.linspace(0.35, 0.97, 10)
    draw_line(rgb, alpha, u, v, [(a, bot_f(a) - 0.006) for a in a2], [0.006 + 0.012 * math.sin(math.pi * (a - 0.35) / 0.62) for a in a2], (0.25, 0.15, 0.12))
    # 二重の線
    a3 = np.linspace(0.32, 0.86, 8)
    draw_line(rgb, alpha, u, v, [(a, top_f(a) + 0.12) for a in a3], [0.004 + 0.008 * math.sin(math.pi * (a - 0.32) / 0.54) for a in a3], (0.42, 0.26, 0.22), 0.8)
    # 画像は sRGB として扱われるので、ここで sRGB に戻して書く
    rgba = np.concatenate([np.clip(rgb, 0, 1) ** (1 / 2.2), np.clip(alpha, 0, 1)[..., None]], -1).astype(np.float32)
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, n, n, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


FACE_W, FACE_H = 0.22, 0.26     # 顔の絵が受け持つ範囲（頭の中心からの x, z）


def face_skin_image(name, skin, brow, male, size=1024):
    """顔の肌の絵：眉・鼻の線・ほほえんだ口・ほお紅（頭の中心からの x, z を u, v に正面から投影）"""
    n = size
    v, u = np.mgrid[0:n, 0:n] / (n - 1)
    X = (u - 0.5) * FACE_W
    Z = (v - 0.5) * FACE_H
    rgb = np.ones((n, n, 3)) * _lin(skin)
    alpha = np.ones((n, n))
    # ほお紅
    for s_ in (-1, 1):
        d = np.sqrt(((X - s_ * 0.05) / 0.017) ** 2 + ((Z + 0.048) / 0.009) ** 2)
        k = _smooth(1.0, 0.0, d) * (0.18 if male else 0.32)
        rgb = rgb * (1 - k[..., None]) + _lin((1.0, 0.55, 0.5))[None, None] * k[..., None]
    rgb = np.ascontiguousarray(rgb)
    bw = 1.5 if male else 1.0
    for s_ in (-1, 1):
        pts = [(s_ * 0.017, 0.012), (s_ * 0.03, 0.019), (s_ * 0.045, 0.0215), (s_ * 0.058, 0.019), (s_ * 0.069, 0.011)]
        draw_line(rgb, alpha, X, Z, pts, [0.0017 * bw, 0.0028 * bw, 0.0026 * bw, 0.002 * bw, 0.0008 * bw], brow)
    # 鼻：鼻先の片側の短い線と、鼻の穴の影
    draw_line(rgb, alpha, X, Z, [(0.0045, -0.031), (0.0068, -0.038), (0.003, -0.0415)], [0.0006, 0.0011, 0.0006], tuple(c * 0.55 for c in skin))
    draw_line(rgb, alpha, X, Z, [(-0.004, -0.0405), (-0.0025, -0.041)], [0.0012, 0.0008], tuple(c * 0.6 for c in skin), 0.8)
    # 口：口角の上がった笑顔、下くちびるの短い線
    mouth = [(-0.0145, -0.0655), (-0.007, -0.0688), (0.0, -0.0696), (0.007, -0.0688), (0.0145, -0.0655)]
    draw_line(rgb, alpha, X, Z, mouth, [0.0006, 0.0012, 0.0013, 0.0012, 0.0006], (0.38, 0.17, 0.14))
    for s_ in (-1, 1):
        draw_line(rgb, alpha, X, Z, [(s_ * 0.0145, -0.0655), (s_ * 0.0165, -0.0645)], [0.0006, 0.0003], (0.38, 0.17, 0.14))
    draw_line(rgb, alpha, X, Z, [(-0.0045, -0.0748), (0.0045, -0.0748)], [0.0004, 0.0004], tuple(c * 0.68 for c in skin), 0.8)
    if male:
        draw_line(rgb, alpha, X, Z, [(-0.008, -0.092), (0.0, -0.0935), (0.008, -0.092)], [0.0004, 0.0007, 0.0004], tuple(c * 0.7 for c in skin), 0.6)
    rgba = np.concatenate([np.clip(rgb, 0, 1) ** (1 / 2.2), np.ones((n, n, 1))], -1).astype(np.float32)
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, n, n, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def opaque_tex_mat(name, img, rough=0.55):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    bsdf = principled(m)
    nt = m.node_tree
    t = next((n_ for n_ in nt.nodes if n_.type == 'TEX_IMAGE'), None) or nt.nodes.new('ShaderNodeTexImage')
    t.image = img
    nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = rough
    m.use_backface_culling = True
    return m
