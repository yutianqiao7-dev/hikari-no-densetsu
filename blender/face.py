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
def lid_top(a, fem):
    """a = 0（目頭）..1（目じり）での上まぶたの高さ（0..1、目の板の中）"""
    k = math.sin(math.pi * min(max(a, 0.0), 1.0))
    peak = 0.5 + 0.43 * (k ** 0.75) + (0.05 if fem else 0.02) * a
    return peak - (0.12 if a < 0.08 else 0.0) * (1 - a / 0.08)


def lid_bot(a, fem):
    k = math.sin(math.pi * min(max(a, 0.0), 1.0))
    return 0.5 - 0.33 * (k ** 1.1) + 0.06 * a


IRIS_C = (0.5, 0.47)        # 虹彩の中心（板の中）
IRIS_R = (0.27, 0.33)       # 横・縦の半径


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def eye_image(name, iris_rgb, fem, size=512):
    """目の絵（RGBA）。行は下から上（Blender の pixels の並び）"""
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
    dx = (u - IRIS_C[0]) / IRIS_R[0]
    dy = (v - IRIS_C[1]) / IRIS_R[1]
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
    for (hx, hy, hr, hk) in ((IRIS_C[0] - 0.1, IRIS_C[1] + 0.14, 0.075, 1.0), (IRIS_C[0] + 0.1, IRIS_C[1] - 0.16, 0.035, 0.85)):
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
