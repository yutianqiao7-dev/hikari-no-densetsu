# -*- coding: utf-8 -*-
"""
ひかりの伝説 — はじまりの村の飾りつけ（ドラクエ10の町のように、にぎやかに）

今の world.blend に足すだけ（何度実行しても同じ結果になるよう、前回の飾りは消してから作る）。
  花壇・石畳の小道・市場の屋台・ベンチ・旗飾り・樽と木箱・立て札・荷車と干し草・村の中の木と茂み・花の群れ
"""
import math, random, importlib, sys, os
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

_here = os.path.dirname(bpy.data.filepath)
if _here not in sys.path:
    sys.path.insert(0, _here)
import bkit
importlib.reload(bkit)
from bkit import MB, mat, B

VX, VZ = 140.0, 110.0
HOUSES = [  # build_world.py の VILLAGE_HOUSES と同じ
    ("Inn", 0, -24, 14, 9, 4.6),
    ("Shop", 24, -15, 9, 7, 3.8),
    ("House1", -24, -15, 8, 7, 3.6),
    ("House2", -25, 15, 8, 7, 3.6),
    ("House3", 25, 16, 9, 7, 3.6),
    ("House4", 2, 26, 10, 7, 3.8),
]
C_BLDG = bpy.data.collections["Buildings"]
C_SCATTER = bpy.data.collections["Scatter"]
C_COL = bpy.data.collections["Colliders"]
PRE = "VDecor"
random.seed(11)

# ---------------------------------------------------------------- 前回の飾りを消す
for ob in list(bpy.data.objects):
    if ob.name.startswith(PRE) or ob.name.startswith("COL_" + PRE) or ".vd" in ob.name:
        bpy.data.objects.remove(ob)

# ---------------------------------------------------------------- 地面の高さ（地形に下向きの光線）
terr = next(o for o in bpy.data.collections["Terrain"].objects if o.type == 'MESH')
dg = bpy.context.evaluated_depsgraph_get()
tm = terr.evaluated_get(dg).to_mesh()
mw = terr.matrix_world
bvh = BVHTree.FromPolygons([mw @ v.co for v in tm.vertices], [p.vertices[:] for p in tm.polygons])


def H(x, z):
    hit = bvh.ray_cast(Vector((x, -z, 500)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] else 0.0


# ---------------------------------------------------------------- 材質
M_WOOD = mat("Wood", (0.42, 0.27, 0.14), 0.8)
M_WOOD_D = mat("WoodDark", (0.25, 0.15, 0.08), 0.8)
M_IRON = mat("Iron", (0.12, 0.12, 0.13), 0.5, 0.8)
M_FLOOR = mat("StoneFloor", (0.66, 0.63, 0.58), 0.9)
M_STONE = mat("Stone", (0.66, 0.62, 0.55), 0.85)
M_PATH = mat("StoneDark", (0.42, 0.4, 0.37), 0.9)       # 小道の石（石壁の質感で、暗め）
M_SOIL = mat("Soil", (0.22, 0.15, 0.1), 0.95)
M_LEAF = mat("Hedge", (0.2, 0.45, 0.16), 0.9)
M_HAY = mat("Hay", (0.86, 0.72, 0.36), 0.95)
M_CLOTH_R = mat("AwningRed", (0.78, 0.16, 0.14), 0.85, double=True)
M_CLOTH_W = mat("AwningWhite", (0.95, 0.93, 0.86), 0.85, double=True)
M_ROPE = mat("Rope", (0.55, 0.45, 0.3), 0.9)
FLOWERS = [mat("FlowerR", (0.95, 0.2, 0.25), 0.6), mat("FlowerY", (1.0, 0.85, 0.2), 0.6), mat("FlowerW", (0.97, 0.97, 0.95), 0.6),
           mat("FlowerP", (0.95, 0.5, 0.75), 0.6), mat("FlowerV", (0.55, 0.4, 0.9), 0.6), mat("FlowerO", (1.0, 0.55, 0.15), 0.6)]
FLAGS = [mat("FlagRed", (0.85, 0.15, 0.15), 0.8, double=True), mat("FlagYellow", (1.0, 0.8, 0.2), 0.8, double=True),
         mat("FlagBlue", (0.2, 0.4, 0.85), 0.8, double=True), mat("FlagGreen", (0.25, 0.65, 0.3), 0.8, double=True),
         mat("FlagWhite", (0.96, 0.96, 0.94), 0.8, double=True)]
FRUIT = [mat("Apple", (0.85, 0.1, 0.1), 0.45), mat("Orange", (1.0, 0.55, 0.1), 0.5), mat("GreenFruit", (0.45, 0.75, 0.2), 0.5),
         mat("Grape", (0.45, 0.2, 0.6), 0.4)]

n_obj = [0]


def build(mb, x, z, rot=0.0, dy=0.0):
    n_obj[0] += 1
    return mb.build(f"{PRE}{n_obj[0]:03d}", C_BLDG, loc=B(x, z, H(x, z) + dy), rot_z=rot)


def collider(x, z, w, d, rot=0.0, top=1.6):
    ob = bpy.data.objects.new(f"COL_{PRE}{n_obj[0]:03d}_{len(C_COL.objects)}", None)
    ob.empty_display_type = 'CUBE'
    C_COL.objects.link(ob)
    ob.location = B(x, z, H(x, z) + top / 2)
    ob.rotation_euler = (0, 0, rot)
    ob.scale = (w / 2, d / 2, top / 2)
    ob.hide_render = True


def face(px, pz):
    return math.atan2(VX - px, VZ - pz)


def local(px, pz, rot, lx, ly):
    """家の向き rot での局所座標（ly < 0 が正面）→ ゲーム座標"""
    bx = px + lx * math.cos(rot) - ly * math.sin(rot)
    by = -pz + lx * math.sin(rot) + ly * math.cos(rot)
    return bx, -by


def flower_blob(mb, x, y, z, s=1.0, cols=None):
    cols = cols or FLOWERS
    mb.add('ico', M_LEAF, loc=(x, y, z), r=0.22 * s, sub=1, scale=(1.3, 1.3, 0.8), jitter=0.04, seed=random.randint(0, 99))
    for k in range(5):
        a = random.uniform(0, math.tau)
        rr = random.uniform(0.05, 0.2) * s
        mb.add('ico', random.choice(cols), loc=(x + math.cos(a) * rr, y + math.sin(a) * rr, z + 0.12 * s + random.uniform(0, 0.06)),
               r=0.06 * s, sub=1)


# ---------------------------------------------------------------- 1. 家の前の花壇・樽と木箱
def barrel(mb, x, y, z=0.0, r=0.42, h=0.95):
    mb.add('cyl', M_WOOD, loc=(x, y, z + h / 2), r1=r * 0.92, r2=r * 0.92, depth=h, seg=16)
    mb.add('cyl', M_WOOD, loc=(x, y, z + h / 2), r1=r, r2=r, depth=h * 0.55, seg=16)
    for hz in (0.12, 0.5, 0.88):
        mb.add('cyl', M_IRON, loc=(x, y, z + h * hz), r1=r * (0.95 if hz != 0.5 else 1.01) + 0.01, r2=r * (0.95 if hz != 0.5 else 1.01) + 0.01, depth=0.05, seg=16)
    mb.add('cyl', M_WOOD_D, loc=(x, y, z + h + 0.005), r1=r * 0.88, r2=r * 0.88, depth=0.02, seg=16)


def crate(mb, x, y, z=0.0, s=0.8, rot=0.0):
    mb.add('cube', M_WOOD, loc=(x, y, z + s / 2), rot=(0, 0, rot), scale=(s, s, s), bevel=0.04)
    c, sn = math.cos(rot), math.sin(rot)
    for (ox, oy) in ((0, -s / 2 - 0.01), (0, s / 2 + 0.01)):
        px, py = x + ox * c - oy * sn, y + ox * sn + oy * c
        mb.add('cube', M_WOOD_D, loc=(px, py, z + s / 2), rot=(0, 0, rot + 0.0), scale=(s * 1.02, 0.04, 0.09))
        mb.add('cube', M_WOOD_D, loc=(px, py, z + s / 2), rot=(0.0, 0.78, rot), scale=(s * 1.25, 0.04, 0.08))


for (nm, dx, dz, w, d, wh) in HOUSES:
    px, pz = VX + dx, VZ + dz
    rot = face(px, pz)
    # 扉の左右に花壇（正面の壁ぎわ）
    for side in (-1, 1):
        lx, ly = side * (w * 0.32), -(d / 2 + 0.35)
        gx, gz = local(px, pz, rot, lx, ly)
        mb = MB()
        L = min(2.2, w * 0.28)
        mb.add('cube', M_WOOD, loc=(0, 0, 0.22), scale=(L, 0.55, 0.44), bevel=0.03)
        mb.add('cube', M_SOIL, loc=(0, 0, 0.42), scale=(L - 0.12, 0.43, 0.06))
        for k in range(int(L / 0.36)):
            flower_blob(mb, -L / 2 + 0.25 + k * 0.36 + random.uniform(-0.05, 0.05), random.uniform(-0.08, 0.08), 0.48, 0.9)
        build(mb, gx, gz, rot)
    # 家の横に樽と木箱
    side = 1 if (sum(ord(c) for c in nm) % 2) else -1
    gx, gz = local(px, pz, rot, side * (w / 2 + 1.0), -d * 0.15)
    mb = MB()
    barrel(mb, 0, 0)
    barrel(mb, 0.85, 0.2, r=0.38, h=0.85)
    crate(mb, -0.2, 0.95, 0, 0.75, 0.2)
    crate(mb, -0.1, 0.95, 0.75, 0.55, -0.3)
    build(mb, gx, gz, rot)
    collider(gx, gz, 2.2, 2.2, rot, 1.4)

# ---------------------------------------------------------------- 2. 広場から家へ続く石畳の小道
paths = []
for (nm, dx, dz, w, d, wh) in HOUSES:
    L = math.hypot(dx, dz)
    ux, uz = -dx / L, -dz / L
    door = (VX + dx + ux * (d / 2 + 1.5), VZ + dz + uz * (d / 2 + 1.5))
    paths.append(door)
paths.append((VX - 44, VZ))
paths.append((VX + 42, VZ + 2))
for (ex, ez) in paths:
    L = math.hypot(ex - VX, ez - VZ)
    ux, uz = (ex - VX) / L, (ez - VZ) / L
    px_, pz_ = -uz, ux
    mb = MB()
    t = 9.8
    gy = H(VX, VZ)
    while t < L - 0.4:
        for lat in (-0.75, 0.0, 0.75):
            jl = lat + random.uniform(-0.12, 0.12)
            x = VX + ux * (t + random.uniform(-0.12, 0.12)) + px_ * jl
            z = VZ + uz * (t + random.uniform(-0.12, 0.12)) + pz_ * jl
            r = random.uniform(0.3, 0.42)
            mb.add('cyl', M_PATH, loc=B(x - VX, z - VZ, H(x, z) - gy + 0.005), rot=(0, 0, random.uniform(0, 6.3)),
                   r1=r, r2=r * 0.9, depth=0.06, seg=7, jitter=0.02, seed=random.randint(0, 999))
        t += 0.78
    n_obj[0] += 1
    mb.build(f"{PRE}{n_obj[0]:03d}", C_BLDG, loc=B(VX, VZ, gy))

# ---------------------------------------------------------------- 3. 市場の屋台（道具屋の前）
def stall(x, z, rot, goods):
    mb = MB()
    W, D, Hh = 3.2, 1.6, 2.4
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.add('cube', M_WOOD_D, loc=(sx * W / 2, sy * D / 2, Hh / 2 + (0.25 if sy > 0 else 0)), scale=(0.12, 0.12, Hh + (0.5 if sy > 0 else 0)))
    mb.add('cube', M_WOOD, loc=(0, -0.1, 0.85), scale=(W + 0.2, D * 0.8, 0.1), bevel=0.02)
    mb.add('cube', M_WOOD, loc=(0, -0.1, 0.45), scale=(W, D * 0.75, 0.75))
    # しま模様の日よけ（前に傾く）
    n = 8
    for k in range(n):
        x0 = -W / 2 - 0.2 + (W + 0.4) * (k + 0.5) / n
        m = M_CLOTH_R if k % 2 == 0 else M_CLOTH_W
        mb.add('cube', m, loc=(x0, -0.1, Hh + 0.32), rot=(-0.32, 0, 0), scale=((W + 0.4) / n + 0.005, D + 0.7, 0.04))
        # 前のふちの波
        mb.add('cyl', m, loc=(x0, -D / 2 - 0.42, Hh + 0.05), rot=(math.pi / 2, 0, 0), r1=(W + 0.4) / n / 2, r2=(W + 0.4) / n / 2, depth=0.04, seg=12)
    # 品物：かごに果物、木箱
    for k, g in enumerate(goods):
        bx = -W / 2 + 0.55 + k * (W - 1.1) / max(1, len(goods) - 1)
        mb.add('cyl', M_HAY, loc=(bx, -0.15, 0.98), r1=0.32, r2=0.26, depth=0.18, seg=14)
        for j in range(9):
            a = j / 9 * math.tau
            rr = 0.16 if j % 3 else 0.0
            mb.add('sphere', g, loc=(bx + math.cos(a) * rr, -0.15 + math.sin(a) * rr, 1.1 + (0.06 if j % 3 == 0 else 0)), r=0.085, seg=10, rings=6)
    crate(mb, W / 2 + 0.5, 0.3, 0, 0.6, 0.3)
    crate(mb, W / 2 + 0.45, 0.35, 0.6, 0.45, -0.2)
    barrel(mb, -W / 2 - 0.55, 0.25, r=0.36, h=0.8)
    build(mb, x, z, rot)
    collider(x, z, W + 1.6, D + 0.6, rot, 2.4)


sx_, sz_ = VX + 24, VZ - 15
rot = face(sx_, sz_)
gx, gz = local(sx_, sz_, rot, -6.2, -5.5)
stall(gx, gz, face(gx, gz), FRUIT)
gx, gz = local(VX - 24, VZ - 15, face(VX - 24, VZ - 15), 6.0, -5.2)
stall(gx, gz, face(gx, gz), [FRUIT[2], FRUIT[0], FRUIT[3]])

# ---------------------------------------------------------------- 4. 広場のまわりのベンチ（道のない方向）
path_angles = sorted(math.atan2(ez - VZ, ex - VX) for (ex, ez) in paths)
gaps = []
for i, a in enumerate(path_angles):
    b = path_angles[(i + 1) % len(path_angles)] + (math.tau if i == len(path_angles) - 1 else 0)
    gaps.append(((a + b) / 2, b - a))
for (a, span) in gaps:
    if span < 0.5:
        continue
    x, z = VX + math.cos(a) * 11.6, VZ + math.sin(a) * 11.6
    mb = MB()
    mb.add('cube', M_WOOD, loc=(0, 0, 0.45), scale=(1.8, 0.45, 0.08), bevel=0.02)
    mb.add('cube', M_WOOD, loc=(0, 0.22, 0.8), rot=(0.18, 0, 0), scale=(1.8, 0.06, 0.38), bevel=0.02)
    for sx in (-0.75, 0.75):
        mb.add('cube', M_IRON, loc=(sx, 0, 0.22), scale=(0.07, 0.42, 0.44))
        mb.add('cube', M_IRON, loc=(sx, 0.22, 0.62), rot=(0.18, 0, 0), scale=(0.06, 0.06, 0.5))
    build(mb, x, z, face(x, z))
    collider(x, z, 1.9, 0.6, face(x, z), 1.0)

# ---------------------------------------------------------------- 5. 家と家の間に三角の旗飾り
pts = []
for (nm, dx, dz, w, d, wh) in HOUSES:
    px, pz = VX + dx, VZ + dz
    rot = face(px, pz)
    for side in (-1, 1):
        gx, gz = local(px, pz, rot, side * (w / 2 - 0.2), -(d / 2 + 0.2))
        pts.append((math.atan2(gz - VZ, gx - VX), gx, gz, H(px, pz) + wh - 0.2))
pts.sort()
gy = H(VX, VZ)
for i in range(len(pts)):
    a0, x0, z0, y0 = pts[i]
    a1, x1, z1, y1 = pts[(i + 1) % len(pts)]
    L = math.hypot(x1 - x0, z1 - z0)
    if L < 3 or L > 30:
        continue
    mb = MB()
    nseg = max(6, int(L / 0.7))
    sag = L * 0.08
    prev = None
    for k in range(nseg + 1):
        t = k / nseg
        x, z = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
        y = y0 + (y1 - y0) * t - sag * 4 * t * (1 - t)
        p = Vector(B(x - VX, z - VZ, y - gy))
        if prev is not None:
            mb.tube([prev, p], [0.012, 0.012], M_ROPE, seg=4)
            # 三角の旗（縄の下に垂れる）
            mid = (prev + p) / 2
            dirv = (p - prev).normalized() * 0.22
            tri = [tuple(mid - dirv), tuple(mid + dirv), tuple(mid + Vector((0, 0, -0.45)))]
            mb.poly(tri, [(0, 1, 2)], FLAGS[k % len(FLAGS)], smooth=False)
        prev = p
    n_obj[0] += 1
    mb.build(f"{PRE}{n_obj[0]:03d}", C_BLDG, loc=B(VX, VZ, gy))

# ---------------------------------------------------------------- 6. 入口の立て札・荷車と干し草
mb = MB()
mb.add('cube', M_WOOD_D, loc=(0, 0, 1.1), scale=(0.14, 0.14, 2.2))
for k, (zz, ang) in enumerate(((1.75, 0.3), (1.35, -0.4))):
    mb.add('cube', M_WOOD, loc=(0.55 * math.cos(ang), 0.55 * math.sin(ang), zz), rot=(0, 0, ang), scale=(1.2, 0.06, 0.28), bevel=0.02)
    mb.add('cyl', M_WOOD, loc=(1.15 * math.cos(ang), 1.15 * math.sin(ang), zz), rot=(0, 0, ang + math.pi / 2), r1=0.2, r2=0.0, depth=0.06, seg=3)
build(mb, VX - 41, VZ + 3.5, 0.4)
collider(VX - 41, VZ + 3.5, 0.6, 0.6, 0, 2.2)

mb = MB()
mb.add('cube', M_WOOD, loc=(0, 0, 0.75), scale=(2.4, 1.3, 0.12), bevel=0.02)
for sy in (-1, 1):
    mb.add('cube', M_WOOD, loc=(0, sy * 0.62, 1.0), scale=(2.4, 0.08, 0.45))
    mb.add('cyl', M_WOOD_D, loc=(-0.3, sy * 0.78, 0.5), rot=(math.pi / 2, 0, 0), r1=0.5, r2=0.5, depth=0.1, seg=16)
    mb.add('cyl', M_IRON, loc=(-0.3, sy * 0.78, 0.5), rot=(math.pi / 2, 0, 0), r1=0.52, r2=0.52, depth=0.06, seg=16)
mb.add('cube', M_WOOD_D, loc=(1.8, 0.35, 0.55), rot=(0, 0.25, 0), scale=(1.6, 0.08, 0.08))
mb.add('cube', M_WOOD_D, loc=(1.8, -0.35, 0.55), rot=(0, 0.25, 0), scale=(1.6, 0.08, 0.08))
for k in range(3):
    mb.add('cube', M_HAY, loc=(-0.5 + k * 0.5, 0, 1.15 + (0.3 if k == 1 else 0)), scale=(0.7, 0.9, 0.45), bevel=0.08)
build(mb, VX + 33, VZ - 7, 0.9)
collider(VX + 33, VZ - 7, 3.0, 1.8, 0.9, 1.6)
mb = MB()
for (x, y, z) in ((0, 0, 0.35), (1.1, 0.2, 0.35), (0.55, 0.1, 1.0)):
    mb.add('cyl', M_HAY, loc=(x, y, z), rot=(math.pi / 2, 0, 0.2), r1=0.6, r2=0.6, depth=1.0, seg=16, bevel=0.05)
build(mb, VX + 31, VZ + 9, 0.3)
collider(VX + 31.5, VZ + 9, 2.2, 1.6, 0.3, 1.6)

# ---------------------------------------------------------------- 7. 村の中の木と茂み・花の群れ（家・道・広場をさける）
def blocked(x, z, pad):
    for (nm, dx, dz, w, d, wh) in HOUSES:
        if math.hypot(x - VX - dx, z - VZ - dz) < max(w, d) * 0.7 + pad:
            return True
    for (ex, ez) in paths:
        L = math.hypot(ex - VX, ez - VZ)
        ux, uz = (ex - VX) / L, (ez - VZ) / L
        t = max(0, min(L, (x - VX) * ux + (z - VZ) * uz))
        if math.hypot(x - VX - ux * t, z - VZ - uz * t) < 2.4 + pad:
            return True
    return math.hypot(x - VX, z - VZ) < 14 + pad


protos = {c.name: c for c in bpy.data.collections["Prototypes"].children}
placed = []
cnt = {"Tree_Broad": 0, "Bush": 0}
for kind, n, rmin, rmax, pad in (("Tree_Broad", 9, 24, 35, 3.5), ("Bush", 26, 16, 36.5, 1.4)):
    tries = 0
    while cnt[kind] < n and tries < 4000:
        tries += 1
        a = random.uniform(0, math.tau)
        r = random.uniform(rmin, rmax)
        x, z = VX + math.cos(a) * r, VZ + math.sin(a) * r
        deg = math.degrees(a) % 360
        if deg < 14 or deg > 346 or 166 < deg < 194:
            continue
        if blocked(x, z, pad) or any(math.hypot(x - px, z - pz) < pr + pad for (px, pz, pr) in placed):
            continue
        placed.append((x, z, pad))
        e = bpy.data.objects.new(f"{kind}.vd{cnt[kind]:03d}", None)
        e.instance_type = 'COLLECTION'
        e.instance_collection = protos[kind]
        C_SCATTER.objects.link(e)
        e.location = B(x, z, H(x, z) - 0.1)
        e.rotation_euler = (0, 0, random.uniform(0, math.tau))
        s = random.uniform(0.8, 1.15) if kind == "Tree_Broad" else random.uniform(0.7, 1.3)
        e.scale = (s, s, s)
        cnt[kind] += 1
        if kind == "Tree_Broad":
            collider(x, z, 0.9 * s, 0.9 * s, 0, 4)
mb = MB()
gy = H(VX, VZ)
for k in range(40):
    for _ in range(50):
        a = random.uniform(0, math.tau)
        r = random.uniform(13, 37)
        x, z = VX + math.cos(a) * r, VZ + math.sin(a) * r
        if not blocked(x, z, 0.4):
            break
    cols = random.sample(FLOWERS, 2)
    for j in range(random.randint(3, 6)):
        fx, fz = x + random.uniform(-0.7, 0.7), z + random.uniform(-0.7, 0.7)
        flower_blob(mb, fx - VX, -(fz - VZ), H(fx, fz) - gy + 0.05, random.uniform(0.7, 1.0), cols)
n_obj[0] += 1
mb.build(f"{PRE}{n_obj[0]:03d}", C_BLDG, loc=B(VX, VZ, gy))
terr.evaluated_get(dg).to_mesh_clear()
print("village decor:", n_obj[0], "objects", cnt)
