# -*- coding: utf-8 -*-
"""
ひかりの伝説 — Blender ワールド生成スクリプト
Blender 5.x の Scripting タブ、または MCP から実行する。

  World       : 地形・海・城・村・塔・木の配置(コレクションインスタンス)・当たり判定(COL_*)・マーカー(MK_*)
  Props       : 木や岩のプロトタイプ
  Characters  : 勇者・NPC・モンスター

座標メモ: ゲーム(Three.js)の (x, y, z) = Blender の (x, z, -y)
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler, noise

random.seed(7)

import os, sys
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\OWNER-1121R\Desktop\クロード\ドラクエ\blender"
sys.path.insert(0, _here)
import importlib, bkit
importlib.reload(bkit)
from bkit import *
from bkit import _mats


# ---------------------------------------------------------------- シーン初期化
def reset():
    for sc in list(bpy.data.scenes)[1:]:
        bpy.data.scenes.remove(sc)
    base = bpy.data.scenes[0]
    base.name = "World"
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights,
                bpy.data.armatures, bpy.data.actions, bpy.data.metaballs):
        for d in list(blk):
            blk.remove(d)
    _mats.clear()
    return base


world_scene = reset()
props_scene = bpy.data.scenes.new("Props")
chars_scene = bpy.data.scenes.new("Characters")


def new_coll(name, scene):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


C_TERRAIN = new_coll("Terrain", world_scene)
C_BLDG = new_coll("Buildings", world_scene)
C_SCATTER = new_coll("Scatter", world_scene)
C_COL = new_coll("Colliders", world_scene)
C_MK = new_coll("Markers", world_scene)
C_PROTO = new_coll("Prototypes", props_scene)
C_CHARS = new_coll("Characters", chars_scene)

# ---------------------------------------------------------------- 地形
SIZE = 640.0
N = 384
HALF = SIZE / 2
STEP = SIZE / N

CASTLE = (-40.0, 60.0)
VILLAGE = (140.0, 110.0)
TOWER = (70.0, -215.0)
LAKE = (-150.0, -30.0)

ROAD_A = [(-40, 92), (-10, 104), (30, 114), (70, 114), (100, 110)]          # 城 → 村
ROAD_B = [(-40, 92), (2, 82), (34, 36), (52, -30), (62, -100), (68, -160), (70, -198)]  # 城 → 塔
ROAD_C = [(34, 36), (0, 0), (-40, -40), (-85, -75), (-120, -100), (-150, -114)]  # 分かれ道 → ほこらの洞窟
ROADS = [ROAD_A, ROAD_B, ROAD_C]
CAVE = (-150.0, -124.0)   # 洞窟の入口

# 村の家（村の中心からの相対位置）: 名前, dx, dz, 幅, 奥行, 壁の高さ, 屋根, 宿屋, 店
VILLAGE_HOUSES = [
    ("Inn", 0, -24, 14, 9, 4.6, 'R', True, False),
    ("Shop", 24, -15, 9, 7, 3.8, 'B', False, True),
    ("House1", -24, -15, 8, 7, 3.6, 'O', False, False),
    ("House2", -25, 15, 8, 7, 3.6, 'G', False, False),
    ("House3", 25, 16, 9, 7, 3.6, 'O', False, False),
    ("House4", 2, 26, 10, 7, 3.8, 'R', False, False),
]


def village_paths():
    vx, vz = 140.0, 110.0
    segs = []
    for (nm, dx, dz, w, d, wh, rm, inn, shop) in VILLAGE_HOUSES:
        L = math.hypot(dx, dz)
        ux, uz = -dx / L, -dz / L
        door = (vx + dx + ux * (d / 2 + 1.5), vz + dz + uz * (d / 2 + 1.5))
        segs.append(((vx, vz), door))
    segs.append(((vx, vz), (vx - 46, vz)))
    segs.append(((vx, vz), (vx + 44, vz + 2)))
    return segs


VILLAGE_PATHS = village_paths()
PADS = [  # (x, z, 半径, 高さ)
    (CASTLE[0], CASTLE[1], 50, 7.0),
    (VILLAGE[0], VILLAGE[1], 46, 4.0),
    (TOWER[0], TOWER[1], 30, 34.0),
]


def seg_dist(px, pz, a, b):
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz)))
    cx, cz = ax + dx * t, az + dz * t
    return math.hypot(px - cx, pz - cz)


def road_dist(x, z):
    return min(seg_dist(x, z, r[i], r[i + 1]) for r in ROADS for i in range(len(r) - 1))


def nz(x, z, s=0.0):
    return noise.noise(Vector((x, z, s)))


def fbm(x, z, o=5, s=0.0):
    t = a = 1.0
    t = 0.0
    f = 1.0
    n = 0.0
    for i in range(o):
        t += a * nz(x * f, z * f, s + i * 7.31)
        n += a
        a *= 0.5
        f *= 2.0
    return t / n


def ridged(x, z, o=5):
    t = 0.0
    a = 1.0
    f = 1.0
    n = 0.0
    for i in range(o):
        t += a * (1.0 - abs(nz(x * f, z * f, 31.0 + i * 3.7)))
        n += a
        a *= 0.5
        f *= 2.0
    return t / n


def height(x, z):
    h = height_raw(x, z)
    rd = road_dist(x, z)
    for (cx, cz, rr, hh) in PADS:
        d = math.hypot(x - cx, z - cz)
        h = lerp(h, hh, smoothstep(rr, rr * 0.62, d))
    # 道は少し窪ませてなだらかに
    if h > 0.5:
        h -= 0.25 * smoothstep(5.0, 1.5, rd)
    return h


def height_raw(x, z):
    r = math.hypot(x, z) / HALF + fbm(x / 90, z / 90, 3, 5.0) * 0.18
    island = smoothstep(0.97, 0.80, r)
    hills = 3.0 + (fbm(x / 110, z / 110, 5) * 0.5 + 0.5) * 12.0
    mtn = smoothstep(-100, -185, z)
    rd = road_dist(x, z)
    corridor = 1.0 - 0.95 * math.exp(-(rd * rd) / (2 * 30 * 30)) * smoothstep(-80, -120, z)
    ridge = ridged(x / 65, z / 65, 5)
    h = hills + mtn * 22.0 + mtn * (ridge ** 2) * 80.0 * corridor
    # 洞窟の入口がある岩山
    h += 17.0 * math.exp(-((x - CAVE[0]) ** 2 + (z - CAVE[1] + 18) ** 2) / (2 * 15 ** 2))
    # 西の湖
    ld = math.hypot(x - LAKE[0], z - LAKE[1]) / 58.0 + fbm(x / 40, z / 40, 3, 9.0) * 0.15
    h = lerp(h, -5.0, smoothstep(1.0, 0.6, ld))
    h = lerp(-14.0, h, island)
    # なだらかな砂浜：海抜 -3〜3.5m の傾斜をゆるめる
    if -3.0 < h < 3.5:
        u = (h + 3.0) / 6.5
        h = -3.0 + 6.5 * (u + 0.12 * math.sin(2 * math.pi * u))
    return h


# 洞窟の前は平らな広場にする（自然の高さに合わせる）
PADS.append((CAVE[0], CAVE[1] + 9, 13, height_raw(CAVE[0], CAVE[1] + 9)))


print("terrain heights...")
heights = [[0.0] * (N + 1) for _ in range(N + 1)]  # [j][i]  j=z, i=x
for j in range(N + 1):
    z = -HALF + j * STEP
    for i in range(N + 1):
        x = -HALF + i * STEP
        heights[j][i] = height(x, z)


def H(x, z):
    fx = (x + HALF) / STEP
    fz = (z + HALF) / STEP
    i = max(0, min(N - 1, int(fx)))
    j = max(0, min(N - 1, int(fz)))
    tx, tz = fx - i, fz - j
    a = lerp(heights[j][i], heights[j][i + 1], tx)
    b = lerp(heights[j + 1][i], heights[j + 1][i + 1], tx)
    return lerp(a, b, tz)


def slope(x, z):
    e = 1.5
    return math.hypot(H(x + e, z) - H(x - e, z), H(x, z + e) - H(x, z - e)) / (2 * e)


def make_terrain():
    verts = []
    for j in range(N + 1):
        z = -HALF + j * STEP
        for i in range(N + 1):
            x = -HALF + i * STEP
            verts.append(B(x, z, heights[j][i]))
    faces = []
    W = N + 1
    for j in range(N):
        for i in range(N):
            a = j * W + i
            faces.append((a, a + 1, a + W + 1, a + W))
    me = bpy.data.meshes.new("Terrain")
    me.from_pydata(verts, [], faces)
    me.update()
    me.shade_smooth()
    # 頂点カラー（草・土・砂・岩・雪）
    GRASS_A = srgb((0.36, 0.62, 0.20))
    GRASS_B = srgb((0.22, 0.46, 0.14))
    FOREST = srgb((0.16, 0.34, 0.11))
    DIRT = srgb((0.56, 0.42, 0.25))
    SAND = srgb((0.88, 0.80, 0.56))
    ROCK = srgb((0.46, 0.44, 0.42))
    SNOW = srgb((0.94, 0.96, 1.0))
    STONE = srgb((0.62, 0.60, 0.56))
    SEABED = srgb((0.60, 0.55, 0.38))

    def mix(a, b, t):
        return tuple(lerp(a[k], b[k], t) for k in range(3))

    cols = []
    for j in range(N + 1):
        z = -HALF + j * STEP
        for i in range(N + 1):
            x = -HALF + i * STEP
            h = heights[j][i]
            s = slope(x, z)
            g = fbm(x / 25, z / 25, 3, 2.0) * 0.5 + 0.5
            c = mix(GRASS_A, GRASS_B, g)
            fm = forest_mask(x, z)
            c = mix(c, FOREST, smoothstep(0.2, 0.7, fm) * 0.8)
            c = mix(c, DIRT, smoothstep(0.55, 0.85, fbm(x / 14, z / 14, 2, 4.0) * 0.5 + 0.5) * 0.35)
            c = mix(c, ROCK, smoothstep(0.45, 0.85, s))
            c = mix(c, SNOW, smoothstep(52, 62, h) * (1 - smoothstep(0.9, 1.3, s)))
            c = mix(c, SAND, smoothstep(2.2, 1.0, h))
            c = mix(c, SEABED, smoothstep(-0.5, -3.0, h))
            rd = road_dist(x, z)
            c = mix(c, DIRT, smoothstep(4.5, 2.0, rd + nz(x / 3, z / 3, 8.0) * 0.8))
            # 城の中庭は石畳
            if abs(x - CASTLE[0]) < 31 and abs(z - CASTLE[1]) < 27:
                c = STONE
            # 魔王の塔のまわりは荒れた岩場
            dt_ = math.hypot(x - TOWER[0], z - TOWER[1])
            c = mix(c, mix(ROCK, srgb((0.3, 0.26, 0.32)), 0.5), smoothstep(30, 18, dt_ + nz(x / 4, z / 4, 6.0) * 3))
            dv = math.hypot(x - VILLAGE[0], z - VILLAGE[1])
            if dv < 42:
                pd = min(seg_dist(x, z, a, b) for (a, b) in VILLAGE_PATHS)
                c = mix(c, DIRT, smoothstep(2.6, 1.0, pd + nz(x / 2, z / 2, 3.0) * 0.6))
                c = mix(c, mix(DIRT, STONE, 0.5), smoothstep(12, 9, dv))
            cols.extend((*c, 1.0))
    ca = me.color_attributes.new("Color", 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set("color", cols)
    me.color_attributes.active_color = ca
    me.materials.append(vcol_mat("Terrain"))
    ob = bpy.data.objects.new("Terrain", me)
    C_TERRAIN.objects.link(ob)

    # 海（ゲーム側で水シェーダーに置き換える）
    wm = bpy.data.meshes.new("Water")
    S2 = 1400
    wm.from_pydata([(-S2, -S2, 0), (S2, -S2, 0), (S2, S2, 0), (-S2, S2, 0)], [], [(0, 1, 2, 3)])
    wm.materials.append(mat("Water", (0.15, 0.45, 0.65), rough=0.05))
    wo = bpy.data.objects.new("Water", wm)
    C_TERRAIN.objects.link(wo)


def forest_mask(x, z):
    east = smoothstep(40, 90, x) * smoothstep(70, 30, z) * smoothstep(-150, -100, z)
    sw = smoothstep(-60, -110, x) * smoothstep(50, 100, z)
    nw = smoothstep(-80, -130, x) * smoothstep(-60, -110, z)
    base = max(east, sw, nw * 0.8)
    n = fbm(x / 45, z / 45, 3, 12.0) * 0.5 + 0.5
    return max(0.0, min(1.0, base * (0.4 + n) + smoothstep(0.62, 0.8, n) * 0.5))


print("terrain mesh...")
make_terrain()

# ---------------------------------------------------------------- 素材
M_STONE = mat("Stone", (0.80, 0.77, 0.70), 0.85)
M_STONE_D = mat("StoneDark", (0.52, 0.50, 0.48), 0.9)
M_ROOF_B = mat("RoofBlue", (0.16, 0.30, 0.72), 0.55)
M_ROOF_R = mat("RoofRed", (0.70, 0.22, 0.16), 0.6)
M_ROOF_O = mat("RoofOrange", (0.80, 0.42, 0.18), 0.6)
M_ROOF_G = mat("RoofGreen", (0.25, 0.48, 0.30), 0.6)
M_WOOD = mat("Wood", (0.42, 0.27, 0.14), 0.8)
M_WOOD_D = mat("WoodDark", (0.25, 0.15, 0.08), 0.8)
M_PLASTER = mat("Plaster", (0.93, 0.89, 0.80), 0.9)
M_DOOR = mat("Door", (0.08, 0.06, 0.05), 0.9)
M_GOLD = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
M_RED = mat("BannerRed", (0.75, 0.10, 0.10), 0.7, double=True)
M_CARPET = mat("Carpet", (0.62, 0.08, 0.10), 0.9)
M_WINDOW = mat("WindowLight", (1.0, 0.82, 0.45), 0.5, emit=(1.0, 0.75, 0.35), emit_strength=2.0)
M_WINDOW_D = mat("WindowDark", (0.10, 0.12, 0.18), 0.3)
M_TOWER = mat("TowerStone", (0.30, 0.27, 0.34), 0.9)
M_TOWER_ROOF = mat("TowerRoof", (0.28, 0.08, 0.36), 0.5)
M_MAGIC = mat("MagicGlow", (0.75, 0.35, 1.0), 0.2, emit=(0.75, 0.30, 1.0), emit_strength=4.0)
M_WATER_WELL = mat("WellWater", (0.15, 0.35, 0.55), 0.05)
M_FLOOR = mat("StoneFloor", (0.66, 0.63, 0.58), 0.9)
M_IRON = mat("Iron", (0.12, 0.12, 0.13), 0.5, 0.8)
M_FLOWER = [mat("FlowerR", (0.95, 0.2, 0.25), 0.6), mat("FlowerY", (1.0, 0.85, 0.2), 0.6), mat("FlowerW", (0.97, 0.97, 0.95), 0.6)]
M_HEDGE = mat("Hedge", (0.2, 0.45, 0.16), 0.9)


def lamp(name, x, z, rot=0.0):
    mb = MB()
    mb.add('cyl', M_IRON, loc=(0, 0, 1.4), r1=0.07, r2=0.05, depth=2.8, seg=8)
    mb.add('cyl', M_IRON, loc=(0, 0, 0.1), r1=0.18, r2=0.14, depth=0.2, seg=8)
    mb.add('cube', M_IRON, loc=(0, -0.25, 2.75), scale=(0.06, 0.5, 0.06))
    mb.add('cube', M_WINDOW, loc=(0, -0.45, 2.45), scale=(0.26, 0.26, 0.36))
    mb.add('cyl', M_IRON, loc=(0, -0.45, 2.72), r1=0.24, r2=0.02, depth=0.2, seg=4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.add('cube', M_IRON, loc=(sx * 0.13, -0.45 + sy * 0.13, 2.45), scale=(0.03, 0.03, 0.38))
    mb.build(name, C_BLDG, loc=B(x, z, H(x, z)), rot_z=rot)
    collider(name, x, z, 0.5, 0.5, top=3)
    lx, ly = 0.0, -0.45
    wx = x + lx * math.cos(rot) - ly * math.sin(rot)
    wy = -z + lx * math.sin(rot) + ly * math.cos(rot)
    marker("Light_" + name, wx, -wy, y=H(x, z) + 2.45)


def gable_roof(mb, w, d, h, y0, m, over=0.6):
    """x 方向に棟がある切妻屋根"""
    w2, d2 = w / 2 + over, d / 2 + over
    t = 0.25
    v = [(-w2, -d2, y0), (w2, -d2, y0), (w2, 0, y0 + h), (-w2, 0, y0 + h),
         (-w2, d2, y0), (w2, d2, y0)]
    # 2 枚の屋根面に厚みを付ける
    for side in (-1, 1):
        a = (-w2, side * d2, y0)
        b = (w2, side * d2, y0)
        c = (w2, 0, y0 + h)
        dd = (-w2, 0, y0 + h)
        verts = [a, b, c, dd,
                 (a[0], a[1], a[2] - t), (b[0], b[1], b[2] - t), (c[0], c[1], c[2] - t), (dd[0], dd[1], dd[2] - t)]
        faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]
        if side > 0:
            faces = [tuple(reversed(f)) for f in faces]
        mb.poly(verts, faces, m)
    # 妻壁
    for sx in (-1, 1):
        x = sx * w / 2
        tri = [(x, -d / 2, y0), (x, d / 2, y0), (x, 0, y0 + h - 0.1)]
        mb.poly(tri, [(0, 1, 2) if sx > 0 else (2, 1, 0)], M_PLASTER)


def collider(name, x, z, w, d, rot=0.0, top=10.0):
    ob = bpy.data.objects.new("COL_" + name, None)
    ob.empty_display_type = 'CUBE'
    C_COL.objects.link(ob)
    ob.location = B(x, z, H(x, z) + top / 2)
    ob.rotation_euler = (0, 0, rot)
    ob.scale = (w / 2, d / 2, top / 2)
    ob.hide_render = True
    return ob


def marker(name, x, z, rot=0.0, y=None):
    e = empty("MK_" + name, C_MK, B(x, z, H(x, z) if y is None else y), rot_z=rot, size=1.0)
    e.empty_display_type = 'SINGLE_ARROW'
    return e


# ---------------------------------------------------------------- 城
def build_castle():
    cx, cz = CASTLE
    y = H(cx, cz)
    mb = MB()
    W, D, WH, T = 64, 56, 9, 2.6

    def box(x, z, w, d, h, m, y0=0.0):
        mb.add('cube', m, loc=B(x, z, y0 + h / 2), scale=(w, d, h))

    # 城壁
    box(0, -D / 2, W, T, WH, M_STONE)
    box(-W / 2, 0, T, D, WH, M_STONE)
    box(W / 2, 0, T, D, WH, M_STONE)
    box(-(W / 4 + 2), D / 2, W / 2 - 4, T, WH, M_STONE)
    box((W / 4 + 2), D / 2, W / 2 - 4, T, WH, M_STONE)
    box(0, D / 2, 8, T, 3.2, M_STONE, WH - 3.2)   # 門の上
    # 狭間（銃眼）
    for sx in range(-15, 16):
        for zz in (-D / 2, D / 2):
            if sx % 2 == 0:
                box(sx * 2.0, zz, 1.2, T + 0.3, 1.2, M_STONE, WH)
    for sz in range(-13, 14):
        for xx in (-W / 2, W / 2):
            if sz % 2 == 0:
                box(xx, sz * 2.0, T + 0.3, 1.2, 1.2, M_STONE, WH)
    # 角の塔
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * W / 2, sz * D / 2
            mb.add('cyl', M_STONE, loc=B(x, z, 7.5), r1=4.6, r2=4.2, depth=15, seg=20)
            mb.add('cyl', M_STONE_D, loc=B(x, z, 15.3), r1=4.9, r2=4.9, depth=0.8, seg=20)
            mb.add('cyl', M_ROOF_B, loc=B(x, z, 19.2), r1=5.6, r2=0.0, depth=7.5, seg=20, smooth=True)
            mb.add('cyl', M_GOLD, loc=B(x, z, 23.4), r1=0.12, r2=0.05, depth=1.4, seg=6)
            for k in range(4):
                a = k * math.pi / 2 + math.pi / 4
                box(x + math.cos(a) * 4.5, z + math.sin(a) * 4.5, 0.6, 0.6, 1.2, M_WINDOW_D, 10)
    # 門の塔
    for sx in (-1, 1):
        x, z = sx * 6.2, D / 2 + 0.5
        mb.add('cyl', M_STONE, loc=B(x, z, 6.5), r1=3.0, r2=2.8, depth=13, seg=16)
        mb.add('cyl', M_ROOF_B, loc=B(x, z, 15.8), r1=3.7, r2=0.0, depth=5.6, seg=16, smooth=True)
    # 中庭の石畳と赤じゅうたん
    box(0, 0, W - 3, D - 3, 0.08, M_FLOOR, -0.02)
    box(0, 11, 3.2, 34, 0.12, M_CARPET, 0.04)
    # 天守
    box(0, -16, 28, 18, 14, M_STONE)
    gable_roof(mb, 28, 18, 6, 14, M_ROOF_B)
    box(0, -6.9, 4.4, 0.4, 6.5, M_DOOR)
    mb.add('cyl', M_DOOR, loc=B(0, -6.9, 6.5), rot=(math.pi / 2, 0, 0), r1=2.2, r2=2.2, depth=0.4, seg=16)
    for wx in (-10, -6, 6, 10):
        for wy in (4.5, 9.5):
            box(wx, -6.9, 1.4, 0.3, 2.4, M_WINDOW, wy)
    for wx in (-3.2, 3.2):
        mb.add('cube', M_RED, loc=B(wx, -6.75, 9.0), scale=(2.0, 0.08, 5.0))
        box(wx, -6.6, 0.5, 0.2, 0.5, M_GOLD, 9.6)
    for sx in (-1, 1):
        x, z = sx * 14, -7.5
        mb.add('cyl', M_STONE, loc=B(x, z, 10), r1=3.4, r2=3.1, depth=20, seg=20)
        mb.add('cyl', M_STONE_D, loc=B(x, z, 20.3), r1=3.7, r2=3.7, depth=0.6, seg=20)
        mb.add('cyl', M_ROOF_B, loc=B(x, z, 25.0), r1=4.2, r2=0.0, depth=9, seg=20, smooth=True)
    mb.add('cyl', M_STONE, loc=B(0, -20, 15), r1=5.6, r2=5.0, depth=30, seg=24)
    mb.add('cyl', M_STONE_D, loc=B(0, -20, 30.3), r1=5.9, r2=5.9, depth=0.8, seg=24)
    mb.add('cyl', M_ROOF_B, loc=B(0, -20, 36.5), r1=6.6, r2=0.0, depth=12, seg=24, smooth=True)
    mb.add('cyl', M_GOLD, loc=B(0, -20, 43.5), r1=0.16, r2=0.05, depth=2.4, seg=6)
    mb.add('cube', M_RED, loc=B(1.6, -20, 43.6), scale=(3.0, 0.06, 1.6))
    for k in range(6):
        a = k * math.pi / 3
        box(math.cos(a) * 5.4, -20 + math.sin(a) * 5.4, 0.9, 0.9, 1.8, M_WINDOW, 22)
    # 中庭の植え込み・噴水
    mb.add('cyl', M_STONE_D, loc=B(-16, 10, 0.4), r1=3.5, r2=3.5, depth=0.8, seg=24)
    mb.add('cyl', M_WATER_WELL, loc=B(-16, 10, 0.75), r1=3.1, r2=3.1, depth=0.1, seg=24)
    mb.add('cyl', M_STONE, loc=B(-16, 10, 1.4), r1=0.5, r2=0.4, depth=2.0, seg=12)
    mb.add('cyl', M_STONE_D, loc=B(16, 10, 0.4), r1=3.5, r2=3.5, depth=0.8, seg=24)
    mb.add('ico', mat("Hedge", (0.20, 0.45, 0.16), 0.9), loc=B(16, 10, 1.6), r=2.4, sub=2, scale=(1, 1, 0.7), jitter=0.25)
    mb.build("Castle", C_BLDG, loc=B(cx, cz, y))

    # 当たり判定
    collider("CastleN", cx, cz - D / 2, W + 4, T + 1, top=WH)
    collider("CastleW", cx - W / 2, cz, T + 1, D + 4, top=WH)
    collider("CastleE", cx + W / 2, cz, T + 1, D + 4, top=WH)
    collider("CastleSW", cx - (W / 4 + 3), cz + D / 2, W / 2 - 3, T + 1, top=WH)
    collider("CastleSE", cx + (W / 4 + 3), cz + D / 2, W / 2 - 3, T + 1, top=WH)
    for sx in (-1, 1):
        for sz in (-1, 1):
            collider(f"CastleT{sx}{sz}", cx + sx * W / 2, cz + sz * D / 2, 9.4, 9.4, top=15)
        collider(f"CastleGate{sx}", cx + sx * 6.2, cz + D / 2 + 0.5, 6, 6, top=13)
        collider(f"CastleKT{sx}", cx + sx * 14, cz - 7.5, 6.8, 6.8, top=20)
    collider("CastleKeep", cx, cz - 17, 29, 20, top=14)
    collider("Fountain", cx - 16, cz + 10, 7, 7, top=2)
    collider("Hedge", cx + 16, cz + 10, 7, 7, top=2)

    marker("Start", cx, cz + D / 2 + 10, rot=math.pi)
    marker("King", cx, cz - 3.2, rot=0.0)
    marker("Guard1", cx - 4.5, cz - 2.5, rot=0.0)
    marker("Guard2", cx + 4.5, cz - 2.5, rot=0.0)
    marker("Guard3", cx - 4.0, cz + D / 2 + 3, rot=0.0)
    marker("Guard4", cx + 4.0, cz + D / 2 + 3, rot=0.0)
    marker("Minister", cx + 9, cz + 4, rot=-math.pi / 2)


# ---------------------------------------------------------------- 村
def build_house(name, x, z, rot, w, d, wh, roof_m, inn=False, shop=False):
    y = H(x, z)
    mb = MB()
    mb.add('cube', M_STONE_D, loc=(0, 0, 0.3), scale=(w + 0.4, d + 0.4, 0.8))
    mb.add('cube', M_PLASTER, loc=(0, 0, 0.7 + wh / 2), scale=(w, d, wh))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.add('cube', M_WOOD_D, loc=(sx * w / 2, sy * d / 2, 0.7 + wh / 2), scale=(0.35, 0.35, wh))
    for sy in (-1, 1):
        mb.add('cube', M_WOOD_D, loc=(0, sy * d / 2, 0.7 + wh), scale=(w, 0.36, 0.3))
        mb.add('cube', M_WOOD_D, loc=(0, sy * d / 2, 0.9), scale=(w, 0.36, 0.25))
    gable_roof(mb, w, d, 2.6 + d * 0.12, 0.7 + wh, roof_m)
    # 扉（正面 = Blender -Y = ゲーム +Z）
    mb.add('cube', M_WOOD, loc=(0, -d / 2 - 0.05, 0.7 + 1.1), scale=(1.4, 0.15, 2.2))
    mb.add('cube', M_GOLD, loc=(0.45, -d / 2 - 0.15, 0.7 + 1.1), scale=(0.12, 0.08, 0.12))
    for wx in (-w / 2 + 1.2, w / 2 - 1.2):
        if abs(wx) > 1.5:
            mb.add('cube', M_WINDOW, loc=(wx, -d / 2 - 0.05, 0.7 + wh * 0.6), scale=(0.9, 0.12, 1.0))
            mb.add('cube', M_WOOD_D, loc=(wx, -d / 2 - 0.12, 0.7 + wh * 0.6 - 0.6), scale=(1.2, 0.3, 0.12))
    for sx in (-1, 1):
        mb.add('cube', M_WINDOW, loc=(sx * (w / 2 + 0.05), 0, 0.7 + wh * 0.6), scale=(0.12, 1.0, 1.0))
    mb.add('cube', M_STONE_D, loc=(w * 0.25, d * 0.2, 0.7 + wh + 2.5), scale=(0.8, 0.8, 2.6))
    if inn or shop:
        mb.add('cyl', M_WOOD_D, loc=(1.6, -d / 2 - 0.8, 0.7 + wh - 0.2), rot=(0, math.pi / 2, 0), r1=0.06, r2=0.06, depth=1.2, seg=6)
        sign = mat("SignInn", (0.85, 0.65, 0.25), 0.5) if inn else mat("SignShop", (0.30, 0.55, 0.85), 0.5)
        mb.add('cube', sign, loc=(2.0, -d / 2 - 0.8, 0.7 + wh - 0.9), scale=(1.2, 0.12, 0.8))
        # 看板マーク
        if inn:
            mb.add('cube', M_PLASTER, loc=(2.0, -d / 2 - 0.88, 0.7 + wh - 0.95), scale=(0.7, 0.05, 0.25))
            mb.add('sphere', M_RED, loc=(1.75, -d / 2 - 0.9, 0.7 + wh - 0.78), r=0.12, seg=10, rings=6)
        else:
            mb.add('cube', M_GOLD, loc=(2.0, -d / 2 - 0.88, 0.7 + wh - 0.9), rot=(0, math.pi / 4, 0), scale=(0.35, 0.05, 0.35))
    for wx in (-w / 2 + 1.2, w / 2 - 1.2):
        if abs(wx) > 1.5:
            mb.add('cube', M_WOOD, loc=(wx, -d / 2 - 0.3, 0.7 + wh * 0.6 - 0.75), scale=(1.1, 0.35, 0.25))
            mb.add('ico', M_HEDGE, loc=(wx, -d / 2 - 0.3, 0.7 + wh * 0.6 - 0.6), r=0.5, sub=1, scale=(1.0, 0.32, 0.22))
            for k in range(5):
                mb.add('ico', M_FLOWER[(k + int(abs(wx))) % 3], loc=(wx - 0.4 + k * 0.2, -d / 2 - 0.36, 0.7 + wh * 0.6 - 0.5), r=0.08, sub=1)
    mb.build(name, C_BLDG, loc=B(x, z, y), rot_z=rot)
    collider(name, x, z, w + 0.8, d + 0.8, rot, top=wh + 3)
    # 煙突の先（ゲーム側で煙を出す）
    lx, ly = w * 0.25, d * 0.2
    cbx = x + lx * math.cos(rot) - ly * math.sin(rot)
    cby = -z + lx * math.sin(rot) + ly * math.cos(rot)
    marker("Smoke_" + name, cbx, -cby, y=y + 0.7 + wh + 3.9)


def build_village():
    vx, vz = VILLAGE

    def face_center(px, pz):
        return math.atan2(vx - px, vz - pz)

    roofs = {'R': M_ROOF_R, 'B': M_ROOF_B, 'O': M_ROOF_O, 'G': M_ROOF_G}
    for (nm, dx, dz, w, d, wh, rk, inn, shop) in VILLAGE_HOUSES:
        px, pz = vx + dx, vz + dz
        build_house(nm, px, pz, face_center(px, pz), w, d, wh, roofs[rk], inn, shop)
    # 広場の石畳
    mb = MB()
    mb.add('cyl', M_FLOOR, loc=(0, 0, -0.02), r1=9.5, r2=9.5, depth=0.1, seg=48)
    mb.build("VillagePlaza", C_BLDG, loc=B(vx, vz, H(vx, vz)))
    # 街灯
    for i, (a, b) in enumerate(VILLAGE_PATHS):
        mx, mz = a[0] + (b[0] - a[0]) * 0.62, a[1] + (b[1] - a[1]) * 0.62
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        lamp(f"VLamp{i}", mx + uz * 2.2, mz - ux * 2.2, math.atan2(-uz, ux))

    # 井戸
    mb = MB()
    mb.add('cyl', M_STONE, loc=(0, 0, 0.5), r1=1.5, r2=1.5, depth=1.0, seg=20)
    mb.add('cyl', M_WATER_WELL, loc=(0, 0, 0.95), r1=1.2, r2=1.2, depth=0.1, seg=20)
    for sx in (-1, 1):
        mb.add('cube', M_WOOD_D, loc=(sx * 1.3, 0, 1.8), scale=(0.2, 0.2, 2.6))
    gable_roof(mb, 3.2, 2.6, 0.9, 3.1, M_ROOF_R, over=0.2)
    mb.build("Well", C_BLDG, loc=B(vx, vz, H(vx, vz)))
    collider("Well", vx, vz, 3.4, 3.4, top=3)

    # 柵（西と東は入り口を空ける）
    R = 38
    mbf = MB()
    n = 72
    for k in range(n):
        a = k / n * math.tau
        px, pz = vx + math.cos(a) * R, vz + math.sin(a) * R
        deg = math.degrees(a) % 360
        if deg < 12 or deg > 348 or 168 < deg < 192:
            continue
        lx, lz = px - vx, pz - vz
        hy = H(px, pz) - H(vx, vz)
        mbf.add('cube', M_WOOD, loc=B(lx, lz, hy + 0.7), scale=(0.25, 0.25, 1.6))
        a2 = (k + 0.5) / n * math.tau
        mx, mz = math.cos(a2) * R, math.sin(a2) * R
        seglen = math.tau * R / n
        for yy in (0.6, 1.15):
            mbf.add('cube', M_WOOD, loc=B(mx, mz, hy + yy), rot=(0, 0, -a2 + math.pi / 2), scale=(0.12, seglen, 0.14))
    mbf.build("VillageFence", C_BLDG, loc=B(vx, vz, H(vx, vz)))
    for k in range(0, n, 3):
        a = k / n * math.tau
        deg = math.degrees(a) % 360
        if deg < 14 or deg > 346 or 166 < deg < 194:
            continue
        collider(f"Fence{k}", vx + math.cos(a) * R, vz + math.sin(a) * R, 4.0, 4.0, top=1.6)

    # 樽・木箱
    mb = MB()
    for (dx, dz) in ((29, -10), (30, -8.6), (-8, -18), (-9.4, -18.6)):
        mb.add('cyl', M_WOOD, loc=B(dx, dz, H(vx + dx, vz + dz) - H(vx, vz) + 0.55), r1=0.5, r2=0.5, depth=1.1, seg=14)
        mb.add('cyl', M_WOOD_D, loc=B(dx, dz, H(vx + dx, vz + dz) - H(vx, vz) + 0.55), r1=0.53, r2=0.53, depth=0.12, seg=14)
    mb.add('cube', M_WOOD, loc=B(20, -8, 0.5), scale=(1.0, 1.0, 1.0))
    mb.add('cube', M_WOOD, loc=B(20.2, -6.9, 0.4), rot=(0, 0, 0.3), scale=(0.8, 0.8, 0.8))
    mb.build("VillageProps", C_BLDG, loc=B(vx, vz, H(vx, vz)))

    marker("Innkeeper", vx + 0, vz - 17.5, rot=face_center(vx, vz - 17.5) * 0)
    marker("Merchant", vx + 20.5, vz - 11, rot=face_center(vx + 20.5, vz - 11))
    marker("Elder", vx - 5, vz + 4, rot=math.pi / 2)
    marker("Girl", vx + 6, vz + 8, rot=-math.pi / 2)
    marker("Villager1", vx - 26, vz + 2, rot=math.pi / 2)
    marker("Villager2", vx + 14, vz + 22, rot=math.pi)
    marker("VillageEntrance", vx - 44, vz, rot=math.pi / 2)


# ---------------------------------------------------------------- 魔王の塔
def build_tower():
    tx, tz = TOWER
    y = H(tx, tz)
    mb = MB()
    mb.add('cyl', M_TOWER, loc=(0, 0, 0.8), r1=14, r2=13, depth=1.6, seg=32)
    mb.add('cyl', M_TOWER, loc=(0, 0, 2.0), r1=11, r2=10.5, depth=1.0, seg=32)
    mb.add('cyl', M_TOWER, loc=(0, 0, 23), r1=9.5, r2=7.2, depth=42, seg=28)
    for hh in (10, 20, 30, 40):
        mb.add('cyl', M_STONE_D, loc=(0, 0, hh), r1=9.7 - hh * 0.055, r2=9.7 - hh * 0.055, depth=0.9, seg=28)
    mb.add('cyl', M_TOWER, loc=(0, 0, 45.2), r1=9.0, r2=9.0, depth=2.0, seg=28)
    for k in range(12):
        a = k / 12 * math.tau
        mb.add('cube', M_TOWER, loc=(math.cos(a) * 8.6, math.sin(a) * 8.6, 47), rot=(0, 0, a), scale=(1.2, 1.4, 1.8))
    mb.add('cyl', M_TOWER_ROOF, loc=(0, 0, 52), r1=6.5, r2=0.0, depth=14, seg=28, smooth=True)
    mb.add('ico', M_MAGIC, loc=(0, 0, 61), r=1.4, sub=1, smooth=False)
    for k in range(10):
        a = k / 10 * math.tau + 0.3
        hh = 8 + k * 3.6
        rr = 9.5 - hh * 0.055
        mb.add('cube', M_MAGIC, loc=(math.cos(a) * rr, math.sin(a) * rr, hh), rot=(0, 0, a), scale=(0.3, 1.0, 1.8))
    # 入口（ゲーム +Z = Blender -Y）
    mb.add('cube', M_DOOR, loc=(0, -9.1, 4.5), scale=(4.0, 1.2, 5.0))
    mb.add('cyl', M_DOOR, loc=(0, -9.1, 7.0), rot=(math.pi / 2, 0, 0), r1=2.0, r2=2.0, depth=1.2, seg=16)
    for sx in (-1, 1):
        mb.add('cube', M_TOWER, loc=(sx * 3.2, -10.2, 5), scale=(1.4, 1.4, 10))
        mb.add('cyl', M_TOWER_ROOF, loc=(sx * 3.2, -10.2, 11), r1=1.0, r2=0.0, depth=2.5, seg=4)
        mb.add('cyl', M_STONE_D, loc=(sx * 5.5, -14, 1.5), r1=0.5, r2=0.4, depth=3, seg=8)
        mb.add('ico', M_MAGIC, loc=(sx * 5.5, -14, 3.6), r=0.5, sub=1, smooth=False)
    # 浮遊する水晶
    for k in range(5):
        a = k / 5 * math.tau
        mb.add('ico', M_MAGIC, loc=(math.cos(a) * 13, math.sin(a) * 13, 5 + (k % 2) * 3), r=0.9, sub=0,
               scale=(0.6, 0.6, 1.6), smooth=False)
    mb.build("DarkTower", C_BLDG, loc=B(tx, tz, y))
    collider("Tower", tx, tz, 19, 19, top=45)
    marker("Boss", tx, tz + 13.5, rot=0.0)
    # 扉をふさぐ闇の封印（ひかりのオーブで消える）
    mb = MB()
    mb.add('cyl', mat("SealGlow", (0.5, 0.1, 0.8), 0.2, emit=(0.6, 0.15, 1.0), emit_strength=3.0, double=True),
           loc=(0, 0, 0), rot=(math.pi / 2, 0, 0), r1=2.3, r2=2.3, depth=0.05, seg=32, scale=(1, 1.55, 1))
    mb.build("TowerSeal", C_BLDG, loc=B(tx, tz + 9.85, y + 4.4))
    marker("TowerDoor", tx, tz + 10.6, rot=0.0)
    marker("TowerExit", tx, tz + 15.5, rot=0.0)

    # 道しるべ
    for (sx, sz, rot, nm) in ((-28, 100, 0.4, "Sign1"), (30, 30, 2.6, "Sign2"), (95, 106, -1.2, "Sign3"), (26, 26, 0.9, "Sign4")):
        mb = MB()
        mb.add('cube', M_WOOD_D, loc=(0, 0, 0.9), scale=(0.18, 0.18, 1.8))
        mb.add('cube', M_WOOD, loc=(0, 0, 1.6), scale=(1.3, 0.12, 0.5))
        mb.build(nm, C_BLDG, loc=B(sx, sz, H(sx, sz)), rot_z=rot)
        marker(nm, sx, sz, rot)
        collider(nm, sx, sz, 1.0, 1.0, top=2)


def build_cave_entrance():
    """岩山に開いた洞窟の入口（南向き）"""
    cx, cz = CAVE
    y = H(cx, cz + 5)
    rock = mat("CaveRock", (0.42, 0.38, 0.34), 0.92)
    rock2 = mat("CaveRockDark", (0.27, 0.24, 0.22), 0.95)
    mb = MB()
    rng = random.Random(77)
    # アーチ状に積んだ大岩
    for k in range(13):
        a = math.pi * k / 12
        px, pz = math.cos(a) * 4.3, -math.sin(a) * 0.4
        mb.add('ico', rock if k % 2 else rock2, loc=(px, pz + 0.6, 0.6 + math.sin(a) * 4.6), r=rng.uniform(1.4, 2.0), sub=2,
               jitter=0.35, smooth=False, seed=k)
    for k in range(10):
        mb.add('ico', rock2, loc=(rng.uniform(-7, 7), rng.uniform(2.5, 7), rng.uniform(0, 6)), r=rng.uniform(2.0, 3.2), sub=2,
               jitter=0.4, smooth=False, seed=40 + k)
    # 暗い奥
    mb.add('sphere', mat("Abyss", (0.0, 0.0, 0.0), 1.0), loc=(0, 2.4, 2.2), r=1.0, seg=24, rings=12, scale=(3.4, 2.0, 3.2))
    # 入口のたいまつ
    for sx in (-1, 1):
        mb.add('cyl', mat("WoodDark", (0.25, 0.15, 0.08), 0.8), loc=(sx * 5.6, -1.2, 1.1), r1=0.1, r2=0.08, depth=2.2, seg=8)
        mb.add('cyl', mat("Iron", (0.12, 0.12, 0.13), 0.5, 0.8), loc=(sx * 5.6, -1.2, 2.3), r1=0.18, r2=0.3, depth=0.3, seg=8)
        marker(f"Light_CaveTorch{sx}", cx + sx * 5.6, cz + 1.2, y=y + 2.5)
        marker(f"Torch_Cave{sx}", cx + sx * 5.6, cz + 1.2, y=y + 2.5)
    mb.build("CaveEntrance", C_BLDG, loc=B(cx, cz, y))
    for sx in (-1, 1):
        collider(f"CaveRockL{sx}", cx + sx * 5.2, cz - 1.0, 3.2, 6.0, top=8)
    collider("CaveBack", cx, cz - 4.5, 14, 3.0, top=8)
    marker("CaveEntrance", cx, cz + 1.2, rot=0.0)
    marker("CaveExit", cx, cz + 6.0, rot=0.0)


build_castle()
build_village()
build_tower()
build_cave_entrance()
for i, (lx, lz) in enumerate([(-47, 97), (-33, 97), (12, 112), (45, 118), (88, 116)]):
    lamp(f"RoadLamp{i}", lx, lz)

# ---------------------------------------------------------------- プロップ（木・岩）
M_BARK = mat("Bark", (0.36, 0.24, 0.14), 0.95)
M_LEAF = mat("Leaf", (0.30, 0.58, 0.20), 0.85)
M_LEAF2 = mat("LeafDark", (0.16, 0.40, 0.18), 0.85)
M_ROCK = mat("Rock", (0.55, 0.53, 0.50), 0.95)
M_MOSS = mat("Moss", (0.34, 0.50, 0.22), 0.95)


def proto(name):
    c = bpy.data.collections.new(name)
    C_PROTO.children.link(c)
    return c


M_LEAFCARD = mat("LeafCard", (0.34, 0.62, 0.22), 0.7, double=True)
M_LEAFCARD2 = mat("LeafCardDark", (0.22, 0.46, 0.2), 0.7, double=True)
M_LEAFCORE = mat("LeafCore", (0.2, 0.4, 0.13), 0.9)


def leaf_cards(name, coll, blobs, m, per=70, size=0.95, seed=1, droop=0.0, parent=None):
    """球状の樹冠の表面に葉っぱのカード（四角形）を貼る。法線は樹冠の中心から外向き（ふんわり陰影）"""
    rng = random.Random(seed)
    verts, faces, uvs, norms = [], [], [], []
    for (c, r) in blobs:
        c = Vector(c)
        for k in range(per):
            zz = rng.uniform(-0.55, 1.0)
            a = rng.uniform(0, math.tau)
            rr = math.sqrt(1 - zz * zz)
            n = Vector((rr * math.cos(a), rr * math.sin(a), zz))
            p = c + n * r * rng.uniform(0.82, 1.06)
            tn = (n + Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(-0.3, 0.5) - droop))).normalized()
            t1 = tn.cross(Vector((0, 0, 1)))
            if t1.length < 1e-3:
                t1 = Vector((1, 0, 0))
            t1.normalize()
            t2 = tn.cross(t1).normalized()
            ang = rng.uniform(0, math.tau)
            t1, t2 = t1 * math.cos(ang) + t2 * math.sin(ang), -t1 * math.sin(ang) + t2 * math.cos(ang)
            sz = size * rng.uniform(0.75, 1.25)
            base = len(verts)
            for (u, v) in ((0, 0), (1, 0), (1, 1), (0, 1)):
                q = p + t1 * (u - 0.5) * sz + t2 * (v - 0.5) * sz
                verts.append(tuple(q))
                uvs.append((u, v))
                norms.append(tuple((q - c).normalized()))
            faces.append((base, base + 1, base + 2, base + 3))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for li, loop in enumerate(me.loops):
        uvl.data[li].uv = uvs[loop.vertex_index]
    me.shade_smooth()
    me.normals_split_custom_set_from_vertices(norms)
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def build_props():
    # 広葉樹
    c = proto("Tree_Broad")
    mb = MB()
    mb.add('cyl', M_BARK, loc=(0, 0, 1.6), r1=0.42, r2=0.26, depth=3.2, seg=10)
    mb.add('cyl', M_BARK, loc=(0.5, 0, 2.6), rot=(0, 0.8, 0), r1=0.16, r2=0.08, depth=1.4, seg=8)
    blobs = [((0, 0, 4.4), 2.3), ((1.3, 0.4, 3.8), 1.6), ((-1.2, -0.3, 3.9), 1.7), ((0.2, -1.1, 3.6), 1.5), ((0.1, 0.9, 5.3), 1.6)]
    for i, (p, r) in enumerate(blobs):
        mb.add('ico', M_LEAFCORE, loc=p, r=r * 0.86, sub=1, jitter=0.3, seed=i * 3)
    tb = mb.build("Tree_Broad", c)
    leaf_cards("Tree_Broad_Leaves", c, blobs, M_LEAFCARD, per=100, size=1.3, seed=11, parent=tb)
    # 針葉樹
    c = proto("Tree_Pine")
    mb = MB()
    mb.add('cyl', M_BARK, loc=(0, 0, 1.2), r1=0.32, r2=0.22, depth=2.4, seg=10)
    tiers = ((2.8, 2.3, 3.2), (4.6, 1.8, 2.8), (6.2, 1.25, 2.4), (7.6, 0.7, 1.8))
    for i, (zz, r, d) in enumerate(tiers):
        mb.add('cyl', M_LEAF2, loc=(0, 0, zz), r1=r * 0.92, r2=0.05, depth=d, seg=12, smooth=True, jitter=0.12, seed=i)
    tp = mb.build("Tree_Pine", c)
    pblobs = []
    for (zz, r, d) in tiers:
        for k in range(3):
            t = k / 3
            pblobs.append(((0, 0, zz - d / 2 + d * t * 0.8 + 0.2), r * (1 - t * 0.75) * 0.95))
    leaf_cards("Tree_Pine_Leaves", c, pblobs, M_LEAFCARD2, per=34, size=0.85, seed=21, droop=0.6, parent=tp)
    # 岩
    c = proto("Rock")
    mb = MB()
    mb.add('ico', M_ROCK, loc=(0, 0, 0.35), r=1.0, sub=2, scale=(1.2, 1.0, 0.75), jitter=0.35, smooth=False, seed=4)
    mb.add('ico', M_ROCK, loc=(0.9, 0.4, 0.15), r=0.5, sub=1, scale=(1, 1, 0.8), jitter=0.15, smooth=False, seed=9)
    mb.build("Rock", c)
    # 茂み
    c = proto("Bush")
    mb = MB()
    bblobs = (((0, 0, 0.5), 0.8), ((0.6, 0.2, 0.4), 0.6), ((-0.5, -0.2, 0.4), 0.65))
    for i, (p, r) in enumerate(bblobs):
        mb.add('ico', M_LEAFCORE, loc=p, r=r * 0.85, sub=2, jitter=0.15, seed=i + 20)
    bo = mb.build("Bush", c)
    leaf_cards("Bush_Leaves", c, bblobs, M_LEAFCARD, per=50, size=0.65, seed=31, parent=bo)

    # 遠景用 LOD（名前の末尾 _LOD のものはゲーム側で遠くの木に使う）
    c = proto("Tree_Broad_LOD")
    mb = MB()
    mb.add('cyl', M_BARK, loc=(0, 0, 1.6), r1=0.42, r2=0.26, depth=3.2, seg=5)
    for i, (p, r) in enumerate(blobs):
        mb.add('ico', M_LEAFCORE, loc=p, r=r * 0.9, sub=1, jitter=0.25, seed=i * 3)
    tbl = mb.build("Tree_Broad_LOD", c)
    leaf_cards("Tree_Broad_LOD_Leaves", c, blobs, M_LEAFCARD, per=20, size=2.3, seed=12, parent=tbl)
    c = proto("Tree_Pine_LOD")
    mb = MB()
    mb.add('cyl', M_BARK, loc=(0, 0, 1.2), r1=0.32, r2=0.22, depth=2.4, seg=5)
    for i, (zz, r, d) in enumerate(((2.8, 2.3, 3.2), (4.6, 1.8, 2.8), (6.2, 1.25, 2.4), (7.6, 0.7, 1.8))):
        mb.add('cyl', M_LEAF2, loc=(0, 0, zz), r1=r * 0.92, r2=0.05, depth=d, seg=7, smooth=True)
    tpl = mb.build("Tree_Pine_LOD", c)
    leaf_cards("Tree_Pine_LOD_Leaves", c, pblobs, M_LEAFCARD2, per=7, size=1.6, seed=22, droop=0.6, parent=tpl)


build_props()


def scatter():
    print("scatter...")
    protos = {c.name: c for c in C_PROTO.children}
    taken = {}
    cell = 4.0

    def free(x, z, r):
        gx, gz = int(x // cell), int(z // cell)
        for i in range(gx - 2, gx + 3):
            for j in range(gz - 2, gz + 3):
                for (ox, oz, orr) in taken.get((i, j), ()):
                    if math.hypot(ox - x, oz - z) < r + orr:
                        return False
        return True

    def take(x, z, r):
        taken.setdefault((int(x // cell), int(z // cell)), []).append((x, z, r))

    def blocked(x, z, pad=0):
        if road_dist(x, z) < 6 + pad:
            return True
        for (cx, cz, rr, _) in PADS:
            if math.hypot(x - cx, z - cz) < rr * 0.85 + pad:
                return True
        return False

    count = {"Tree_Broad": 0, "Tree_Pine": 0, "Rock": 0, "Bush": 0}
    for k in range(60000):
        x = random.uniform(-HALF + 10, HALF - 10)
        z = random.uniform(-HALF + 10, HALF - 10)
        h = H(x, z)
        if h < 1.6 or h > 48:
            continue
        s = slope(x, z)
        fm = forest_mask(x, z)
        r = random.random()
        kind = None
        if s < 0.55 and r < fm * 0.9 + 0.02:
            kind = "Tree_Pine" if (h > 20 or random.random() < 0.25) else "Tree_Broad"
            rad = 2.2
        elif r < 0.035:
            kind = "Rock"
            rad = 1.5
        elif r < 0.05 + fm * 0.05 and s < 0.5:
            kind = "Bush"
            rad = 1.2
        if not kind or blocked(x, z) or not free(x, z, rad):
            continue
        take(x, z, rad)
        e = bpy.data.objects.new(f"{kind}.{count[kind]:04d}", None)
        e.instance_type = 'COLLECTION'
        e.instance_collection = protos[kind]
        C_SCATTER.objects.link(e)
        e.location = B(x, z, h - 0.1)
        e.rotation_euler = (0, 0, random.uniform(0, math.tau))
        sc = random.uniform(0.75, 1.35) if kind.startswith("Tree") else random.uniform(0.6, 1.8)
        e.scale = (sc, sc, sc * random.uniform(0.9, 1.15))
        count[kind] += 1
    print(count)


scatter()

# キャラクターは build_characters.py、モンスターは build_monsters.py で生成する

# ---------------------------------------------------------------- ビューのための簡易ライト
for sc in (world_scene, props_scene, chars_scene):
    ld = bpy.data.lights.new("Sun_" + sc.name, 'SUN')
    ld.energy = 3.5
    lo = bpy.data.objects.new("Sun_" + sc.name, ld)
    lo.rotation_euler = (math.radians(50), 0, math.radians(30))
    sc.collection.objects.link(lo)
C_COL.hide_render = True
for vl in world_scene.view_layers:
    vl.layer_collection.children["Colliders"].hide_viewport = True

print("build done")
