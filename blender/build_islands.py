# -*- coding: utf-8 -*-
"""
ひかりの伝説 第二部 — 竜で渡る 4 つの島（build_world.py の後に実行）

  desert  灼砂の島 サンドラ    : 砂丘・オアシスの町・ファラオのピラミッド・遺跡
  ice     氷雪の島 フロスティア : 雪原・氷河の山・凍った湖・ゆきの村・氷の宮殿
  volcano 炎獄の島 ボルカニア   : 火山と火口の溶岩湖・溶岩の川・かじやの里・火口の洞窟
  dark    闇の島 ネクロス       : 荒れ地・墓地・闇の水晶・レジスタンスの砦・混沌の城

各島はそれぞれ自分の原点を中心にした 480m 四方の地形を持ち、ゲーム側で海の上の位置に並べる。
コレクション I_<島>_Terrain / Buildings / Scatter / Colliders / Markers に分け、export_game.py が
public/assets/island_<島>.glb と island_<島>.json に書き出す。
マーカー名は MK_<島>__<名前>、当たり判定は COL_<島>__<名前>。
"""
import os, sys, math, random, json
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\OWNER-1121R\Desktop\クロード\ドラクエ\blender"
sys.path.insert(0, _here)
import importlib, bkit
importlib.reload(bkit)
from bkit import *
import bpy, bmesh
from mathutils import Vector, noise

SIZE = 480.0
NSEG = 320
HALF = SIZE / 2
STEP = SIZE / NSEG
ISLAND_IDS = ["desert", "ice", "volcano", "dark"]

# ---------------------------------------------------------------- 後始末（再実行用）
for ob in list(bpy.data.objects):
    if ob.name.startswith(("MK_desert", "MK_ice", "MK_volcano", "MK_dark", "COL_desert", "COL_ice", "COL_volcano", "COL_dark")) \
            or any(ob.users_collection and c.name.startswith("I_") for c in ob.users_collection):
        bpy.data.objects.remove(ob)
for c in list(bpy.data.collections):
    if c.name.startswith("I_") or c.name.startswith("IP_"):
        bpy.data.collections.remove(c)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)

if "Islands" in bpy.data.scenes:
    ISL_SCENE = bpy.data.scenes["Islands"]
else:
    ISL_SCENE = bpy.data.scenes.new("Islands")
C_PROTO = bpy.data.collections["Prototypes"]


def nz(x, z, s=0.0):
    return noise.noise(Vector((x, z, s)))


def fbm(x, z, o=5, s=0.0):
    t = 0.0
    a = 1.0
    f = 1.0
    n = 0.0
    for i in range(o):
        t += a * nz(x * f, z * f, s + i * 7.31)
        n += a
        a *= 0.5
        f *= 2.0
    return t / n


def ridged(x, z, o=5, s=0.0):
    t = 0.0
    a = 1.0
    f = 1.0
    n = 0.0
    for i in range(o):
        t += a * (1.0 - abs(nz(x * f, z * f, 31.0 + s + i * 3.7)))
        n += a
        a *= 0.5
        f *= 2.0
    return t / n


def seg_dist(px, pz, a, b):
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz + 1e-9)))
    return math.hypot(px - (ax + dx * t), pz - (az + dz * t))


def poly_dist(px, pz, pts):
    return min(seg_dist(px, pz, pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


# ================================================================== 島の共通部分
class Island:
    def __init__(self, iid, seed):
        self.id = iid
        self.rng = random.Random(seed)
        self.seed = seed
        self.pads = []     # (x, z, r, h)
        self.paths = []    # [(x, z), ...]
        self.no_scatter = []  # (x, z, r)
        self.areas = {}
        self.npcs = {}
        self.signs = {}
        mk = lambda nm: self._coll(f"I_{iid}_{nm}")
        self.C_T, self.C_B, self.C_S, self.C_C, self.C_M = mk("Terrain"), mk("Buildings"), mk("Scatter"), mk("Colliders"), mk("Markers")

    def _coll(self, name):
        c = bpy.data.collections.new(name)
        ISL_SCENE.collection.children.link(c)
        return c

    # ---------------- 地形
    def land(self, x, z):
        raise NotImplementedError

    def island_mask(self, x, z, r0=205.0):
        r = math.hypot(x, z) / r0 + fbm(x / 80, z / 80, 3, self.seed * 1.3) * 0.16
        return smoothstep(1.0, 0.8, r)

    def height_raw(self, x, z):
        m = self.island_mask(x, z)
        h = lerp(-13.0, self.land(x, z), m)
        if -3.0 < h < 3.5:
            u = (h + 3.0) / 6.5
            h = -3.0 + 6.5 * (u + 0.12 * math.sin(2 * math.pi * u))
        return h

    def height(self, x, z):
        h = self.height_raw(x, z)
        for (cx, cz, rr, hh) in self.pads:
            d = math.hypot(x - cx, z - cz)
            h = lerp(h, hh, smoothstep(rr, rr * 0.62, d))
        if self.paths and h > 0.8:
            pd = self.path_dist(x, z)
            h -= 0.2 * smoothstep(4.0, 1.2, pd)
        return h

    def path_dist(self, x, z):
        if not self.paths:
            return 1e9
        return min(poly_dist(x, z, p) for p in self.paths)

    def pad_here(self, x, z, r, extra=0.0):
        """自然な高さに合わせた平らな場所"""
        h = self.height_raw(x, z) + extra
        self.pads.append((x, z, r, h))
        return h

    def compute(self):
        print(self.id, "heights...")
        W = NSEG + 1
        self.hs = [[0.0] * W for _ in range(W)]
        for j in range(W):
            z = -HALF + j * STEP
            for i in range(W):
                x = -HALF + i * STEP
                self.hs[j][i] = self.height(x, z)

    def H(self, x, z):
        fx = (x + HALF) / STEP
        fz = (z + HALF) / STEP
        i = max(0, min(NSEG - 1, int(fx)))
        j = max(0, min(NSEG - 1, int(fz)))
        tx, tz = fx - i, fz - j
        a = lerp(self.hs[j][i], self.hs[j][i + 1], tx)
        b = lerp(self.hs[j + 1][i], self.hs[j + 1][i + 1], tx)
        return lerp(a, b, tz)

    def slope(self, x, z):
        e = 1.5
        return math.hypot(self.H(x + e, z) - self.H(x - e, z), self.H(x, z + e) - self.H(x, z - e)) / (2 * e)

    def color(self, x, z, h, s):
        raise NotImplementedError

    def make_terrain(self):
        W = NSEG + 1
        verts = []
        for j in range(W):
            z = -HALF + j * STEP
            for i in range(W):
                x = -HALF + i * STEP
                verts.append(B(x, z, self.hs[j][i]))
        faces = []
        for j in range(NSEG):
            for i in range(NSEG):
                a = j * W + i
                faces.append((a, a + 1, a + W + 1, a + W))
        me = bpy.data.meshes.new(f"Terrain_{self.id}")
        me.from_pydata(verts, [], faces)
        me.update()
        me.shade_smooth()
        cols = []
        for j in range(W):
            z = -HALF + j * STEP
            for i in range(W):
                x = -HALF + i * STEP
                h = self.hs[j][i]
                c = self.color(x, z, h, self.slope(x, z))
                cols.extend((*c, 1.0))
        ca = me.color_attributes.new("Color", 'FLOAT_COLOR', 'POINT')
        ca.data.foreach_set("color", cols)
        me.color_attributes.active_color = ca
        me.materials.append(vcol_mat("Terrain"))
        ob = bpy.data.objects.new(f"Terrain_{self.id}", me)
        self.C_T.objects.link(ob)

    # ---------------- 配置
    def marker(self, name, x, z, rot=0.0, y=None):
        e = empty(f"MK_{self.id}__{name}", self.C_M, B(x, z, self.H(x, z) if y is None else y), rot_z=rot, size=1.0)
        e.empty_display_type = 'SINGLE_ARROW'
        return e

    def collider(self, name, x, z, w, d, rot=0.0, top=10.0):
        ob = bpy.data.objects.new(f"COL_{self.id}__{name}", None)
        ob.empty_display_type = 'CUBE'
        self.C_C.objects.link(ob)
        ob.location = B(x, z, self.H(x, z) + top / 2)
        ob.rotation_euler = (0, 0, rot)
        ob.scale = (w / 2, d / 2, top / 2)
        return ob

    def build(self, mb, name, x, z, rot=0.0, y=None):
        ob = mb.build(f"{self.id}_{name}", self.C_B, loc=B(x, z, self.H(x, z) if y is None else y), rot_z=rot)
        return ob

    def npc(self, nid, model, x, z, rot=0.0, wander=False, rng_=3.0):
        self.marker(f"NPC_{nid}", x, z, rot)
        self.npcs[nid] = {"model": model, "wander": wander, "range": rng_}

    def area(self, key, name, x, z, r, music="town"):
        self.marker(f"Area_{key}_{int(r)}", x, z)
        self.areas[key] = {"name": name, "music": music}

    def scatter(self, rules, tries=45000):
        """rules: [(kind, weight_fn(x,z,h,s) -> 確率, 半径, (最小スケール, 最大))]"""
        protos = {c.name: c for c in C_PROTO.children}
        taken = {}
        cell = 4.0
        count = {}

        def free(x, z, r):
            gx, gz = int(x // cell), int(z // cell)
            for i in range(gx - 2, gx + 3):
                for j in range(gz - 2, gz + 3):
                    for (ox, oz, orr) in taken.get((i, j), ()):
                        if math.hypot(ox - x, oz - z) < r + orr:
                            return False
            return True

        rng = self.rng
        for k in range(tries):
            x = rng.uniform(-HALF + 12, HALF - 12)
            z = rng.uniform(-HALF + 12, HALF - 12)
            h = self.H(x, z)
            if h < 1.4:
                continue
            if self.path_dist(x, z) < 5:
                continue
            if any(math.hypot(x - cx, z - cz) < rr * 0.9 for (cx, cz, rr, _) in self.pads):
                continue
            if any(math.hypot(x - cx, z - cz) < rr for (cx, cz, rr) in self.no_scatter):
                continue
            s = self.slope(x, z)
            r = rng.random()
            acc = 0.0
            pick = None
            for (kind, fn, rad, sc) in rules:
                acc += fn(x, z, h, s)
                if r < acc:
                    pick = (kind, rad, sc)
                    break
            if not pick:
                continue
            kind, rad, sc = pick
            if not free(x, z, rad):
                continue
            taken.setdefault((int(x // cell), int(z // cell)), []).append((x, z, rad))
            e = bpy.data.objects.new(f"{self.id}_{kind}.{count.get(kind, 0):04d}", None)
            e.instance_type = 'COLLECTION'
            e.instance_collection = protos[kind]
            self.C_S.objects.link(e)
            e.location = B(x, z, h - 0.1)
            e.rotation_euler = (0, 0, rng.uniform(0, math.tau))
            s_ = rng.uniform(*sc)
            e.scale = (s_, s_, s_ * rng.uniform(0.9, 1.12))
            count[kind] = count.get(kind, 0) + 1
        print(self.id, "scatter", count)

    def save_meta(self):
        self.C_T["meta"] = json.dumps({"areas": self.areas, "npcs": self.npcs, "signs": self.signs}, ensure_ascii=False)


# ================================================================== 島のプロップ（木・岩など）
def proto(name):
    if name in bpy.data.collections:
        old = bpy.data.collections[name]
        for ob in list(old.objects):
            bpy.data.objects.remove(ob)
        bpy.data.collections.remove(old)
    c = bpy.data.collections.new(name)
    C_PROTO.children.link(c)
    return c


def leaf_fan(mb, base, direction, length, width, m, segs=6, droop=0.35, leaflets=11):
    """ヤシの葉：中心の葉軸に沿って両側に小葉を並べる（両面）"""
    d = Vector(direction).normalized()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    pts = []
    for k in range(segs + 1):
        t = k / segs
        p = Vector(base) + d * length * t + Vector((0, 0, -droop * length * t * t))
        pts.append(p)
    mb.tube(pts, [0.05 * (1 - t * 0.8) for t in [k / segs for k in range(segs + 1)]], m, seg=5)
    verts, faces = [], []
    for k in range(1, leaflets + 1):
        t = k / (leaflets + 1)
        idx = t * segs
        a = int(idx)
        b = min(segs, a + 1)
        p = pts[a].lerp(pts[b], idx - a)
        w = width * math.sin(t * math.pi) * (1.1 - t * 0.4)
        for sx in (-1, 1):
            tip = p + side * sx * w + d * 0.25 * w + Vector((0, 0, -0.35 * w))
            base_i = len(verts)
            verts += [tuple(p - d * 0.1), tuple(p + d * 0.12), tuple(tip)]
            faces.append((base_i, base_i + 1, base_i + 2))
    mb.poly(verts, faces, m, smooth=True)


def build_island_props():
    # ---- ヤシの木
    trunk = mat("PalmTrunk", (0.52, 0.4, 0.26), 0.9)
    frond = mat("PalmLeaf", (0.32, 0.56, 0.2), 0.7, double=True)
    coco = mat("Coconut", (0.35, 0.24, 0.12), 0.7)
    for lod in (False, True):
        c = proto("TreePalm_LOD" if lod else "TreePalm")
        mb = MB()
        pts = [Vector((0.18 * math.sin(t * 2.2) * t * 2, 0.1 * t, t * 7.5)) for t in [k / 8 for k in range(9)]]
        mb.tube(pts, [0.32 - 0.12 * (k / 8) for k in range(9)], trunk, seg=6 if lod else 10)
        if not lod:
            for k in range(1, 8):
                p = pts[k]
                mb.add('cyl', trunk, loc=tuple(p), r1=0.3 - 0.11 * (k / 8) + 0.04, r2=0.3 - 0.11 * (k / 8), depth=0.25, seg=10)
        top = pts[-1]
        nf = 9
        for k in range(nf):
            a = k / nf * math.tau + 0.3
            el = 0.35 if k % 2 else 0.05
            d = Vector((math.cos(a), math.sin(a), el))
            leaf_fan(mb, top, d, 3.6, 0.75, frond, segs=4 if lod else 6, droop=0.4, leaflets=5 if lod else 11)
        for k in range(4):
            a = k / 4 * math.tau
            mb.add('sphere', coco, loc=tuple(top + Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, -0.35))), r=0.2, seg=8, rings=6)
        mb.build("TreePalm_LOD" if lod else "TreePalm", c)

    # ---- サボテン
    cg = mat("CactusGreen", (0.25, 0.48, 0.24), 0.75)
    cf = mat("CactusFlower", (1.0, 0.45, 0.6), 0.6)
    c = proto("Cactus")
    mb = MB()
    mb.add('cyl', cg, loc=(0, 0, 1.6), r1=0.42, r2=0.38, depth=3.2, seg=12)
    mb.add('sphere', cg, loc=(0, 0, 3.2), r=0.38, seg=12, rings=6, scale=(1, 1, 0.8))
    for sx, hh, ln in ((1, 1.3, 1.4), (-1, 1.9, 1.1)):
        mb.tube([(0, 0, hh), (sx * 0.7, 0, hh), (sx * 0.85, 0, hh + 0.3), (sx * 0.85, 0, hh + ln)], [0.24, 0.24, 0.24, 0.24], cg, seg=10)
        mb.add('sphere', cg, loc=(sx * 0.85, 0, hh + ln), r=0.24, seg=10, rings=6)
    mb.add('ico', cf, loc=(0.1, -0.1, 3.45), r=0.14, sub=1)
    mb.build("Cactus", c)

    # ---- 砂岩
    sand_r = mat("SandRock", (0.72, 0.5, 0.32), 0.95)
    sand_r2 = mat("SandRockDark", (0.55, 0.36, 0.24), 0.95)
    c = proto("RockDune")
    mb = MB()
    mb.add('ico', sand_r, loc=(0, 0, 0.6), r=1.2, sub=2, scale=(1.3, 1.0, 0.8), jitter=0.3, smooth=False, seed=3)
    mb.add('ico', sand_r2, loc=(0.9, 0.5, 0.3), r=0.6, sub=1, jitter=0.15, smooth=False, seed=8)
    for k in range(3):
        mb.add('cube', sand_r2, loc=(0, 0, 0.25 + k * 0.35), rot=(0, 0, 0.3 * k), scale=(2.6 - k * 0.5, 2.0 - k * 0.4, 0.06))
    mb.build("RockDune", c)

    # ---- 雪の針葉樹
    bark = mat("SnowBark", (0.3, 0.22, 0.16), 0.95)
    needle = mat("LeafPineSnow", (0.12, 0.3, 0.2), 0.85)
    snow = mat("SnowCap", (0.95, 0.97, 1.0), 0.6)
    for lod in (False, True):
        c = proto("TreeSnowPine_LOD" if lod else "TreeSnowPine")
        mb = MB()
        mb.add('cyl', bark, loc=(0, 0, 1.2), r1=0.3, r2=0.2, depth=2.4, seg=6 if lod else 10)
        tiers = ((2.6, 2.4, 3.0), (4.3, 1.9, 2.7), (5.9, 1.35, 2.3), (7.3, 0.8, 1.8))
        for i, (zz, r, d) in enumerate(tiers):
            mb.add('cyl', needle, loc=(0, 0, zz), r1=r, r2=0.05, depth=d, seg=7 if lod else 12, smooth=not lod, jitter=0 if lod else 0.12, seed=i)
            # 雪のかさ（上半分を白く）
            mb.add('cyl', snow, loc=(0, 0, zz + d * 0.18), r1=r * 0.78, r2=0.04, depth=d * 0.62, seg=7 if lod else 12, smooth=not lod, jitter=0 if lod else 0.1, seed=i + 9)
        mb.build("TreeSnowPine_LOD" if lod else "TreeSnowPine", c)

    # ---- 氷の結晶
    ice = mat("IceCrystal", (0.62, 0.86, 1.0), 0.08, emit=(0.35, 0.7, 1.0), emit_strength=0.8)
    c = proto("RockIce")
    mb = MB()
    rng = random.Random(5)
    for k in range(6):
        a = rng.uniform(0, math.tau)
        tilt = rng.uniform(0.1, 0.6)
        ln = rng.uniform(1.4, 3.2)
        d = Vector((math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt)))
        base = Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 0))
        q = Vector((0, 0, 1)).rotation_difference(d)
        mb.add('cyl', ice, loc=tuple(base + d * ln * 0.4), rot=tuple(q.to_euler()), r1=0.35, r2=0.3, depth=ln * 0.8, seg=6, smooth=False)
        mb.add('cyl', ice, loc=tuple(base + d * ln * 0.9), rot=tuple(q.to_euler()), r1=0.3, r2=0.0, depth=ln * 0.25, seg=6, smooth=False)
    mb.build("RockIce", c)

    # ---- 雪の積もった岩
    srock = mat("SnowRock", (0.45, 0.47, 0.52), 0.95)
    c = proto("RockSnow")
    mb = MB()
    mb.add('ico', srock, loc=(0, 0, 0.5), r=1.1, sub=2, scale=(1.3, 1.0, 0.75), jitter=0.3, smooth=False, seed=12)
    mb.add('ico', snow, loc=(0, 0, 0.95), r=1.0, sub=2, scale=(1.2, 0.95, 0.35), jitter=0.1, seed=13)
    mb.build("RockSnow", c)

    # ---- 焼けた木
    char = mat("CharredWood", (0.09, 0.07, 0.06), 0.95)
    ember = mat("EmberGlow", (1.0, 0.35, 0.05), 0.5, emit=(1.0, 0.3, 0.05), emit_strength=3.0)
    c = proto("TreeDead")
    mb = MB()
    mb.tube([(0, 0, 0), (0.1, 0, 2.0), (-0.1, 0.1, 3.8), (0.2, 0.1, 5.2)], [0.35, 0.28, 0.18, 0.06], char, seg=8)
    for (p, d, ln) in (((0.05, 0, 2.6), (1, 0.2, 0.8), 1.8), ((-0.05, 0.05, 3.4), (-1, -0.3, 0.9), 1.5), ((0.1, 0.1, 4.3), (0.4, 1, 0.9), 1.2)):
        dv = Vector(d).normalized()
        mb.tube([p, tuple(Vector(p) + dv * ln * 0.5), tuple(Vector(p) + dv * ln + Vector((0, 0, 0.3)))], [0.12, 0.08, 0.02], char, seg=6)
    mb.add('cube', ember, loc=(0.05, -0.33, 1.2), rot=(0, 0.2, 0), scale=(0.06, 0.02, 0.5))
    mb.build("TreeDead", c)

    # ---- 溶岩の割れ目がある岩
    basalt = mat("Basalt", (0.12, 0.11, 0.11), 0.9)
    lavag = mat("LavaCrack", (1.0, 0.4, 0.08), 0.6, emit=(1.0, 0.35, 0.05), emit_strength=4.0)
    c = proto("RockLava")
    mb = MB()
    mb.add('ico', basalt, loc=(0, 0, 0.55), r=1.2, sub=2, scale=(1.3, 1.1, 0.8), jitter=0.35, smooth=False, seed=21)
    for k in range(4):
        a = k * 1.7
        mb.add('cube', lavag, loc=(math.cos(a) * 0.9, math.sin(a) * 0.7, 0.4 + k * 0.1), rot=(0.3, 0.5, a), scale=(0.08, 0.9, 0.05))
    mb.build("RockLava", c)

    # ---- 玄武岩の柱
    c = proto("RockBasalt")
    mb = MB()
    rng = random.Random(9)
    for k in range(9):
        a = k / 9 * math.tau
        rr = 0.0 if k == 0 else rng.uniform(0.6, 1.1)
        hh = rng.uniform(1.0, 3.6)
        mb.add('cyl', basalt, loc=(math.cos(a) * rr, math.sin(a) * rr, hh / 2), r1=0.42, r2=0.42, depth=hh, seg=6, smooth=False)
    mb.build("RockBasalt", c)

    # ---- 闇の島：ねじれた木
    dbark = mat("DarkBark", (0.16, 0.12, 0.16), 0.95)
    dleaf = mat("LeafDark2", (0.25, 0.18, 0.3), 0.8)
    for lod in (False, True):
        c = proto("TreeDark_LOD" if lod else "TreeDark")
        mb = MB()
        mb.tube([(0, 0, 0), (0.3, 0.1, 1.6), (-0.2, 0.3, 3.0), (0.3, 0.0, 4.4)], [0.42, 0.3, 0.2, 0.08], dbark, seg=6 if lod else 9)
        rng = random.Random(4)
        for k in range(6):
            a = k / 6 * math.tau
            h0 = 2.2 + (k % 3) * 0.7
            p0 = Vector((0.05, 0.15, h0))
            p1 = p0 + Vector((math.cos(a) * 1.1, math.sin(a) * 1.1, 0.5))
            p2 = p1 + Vector((math.cos(a + 0.6) * 0.9, math.sin(a + 0.6) * 0.9, -0.1 + rng.uniform(-0.2, 0.5)))
            mb.tube([p0, p1, p2], [0.12, 0.06, 0.015], dbark, seg=5)
            if not lod:
                mb.add('ico', dleaf, loc=tuple(p2), r=0.35, sub=1, jitter=0.1, seed=k)
        mb.build("TreeDark_LOD" if lod else "TreeDark", c)

    # ---- 墓石
    gstone = mat("GraveStone", (0.42, 0.42, 0.45), 0.9)
    moss = mat("GraveMoss", (0.25, 0.3, 0.2), 0.95)
    c = proto("RockGrave")
    mb = MB()
    mb.add('cube', gstone, loc=(0, 0, 0.7), rot=(0.06, 0.03, 0), scale=(0.75, 0.22, 1.2))
    mb.add('cyl', gstone, loc=(0, 0, 1.3), rot=(math.pi / 2, 0, 0.03), r1=0.375, r2=0.375, depth=0.22, seg=14, scale=(1, 1, 1))
    mb.add('cube', gstone, loc=(0, 0, 0.08), scale=(1.0, 0.5, 0.16))
    mb.add('ico', moss, loc=(0.2, -0.05, 0.25), r=0.25, sub=1, scale=(1.4, 0.7, 0.5))
    mb.add('cube', gstone, loc=(0.85, 0.2, 0.55), rot=(0, 0, 0.3), scale=(0.12, 0.12, 1.1))
    mb.add('cube', gstone, loc=(0.85, 0.2, 0.85), rot=(0, 0, 0.3), scale=(0.5, 0.12, 0.12))
    mb.build("RockGrave", c)

    # ---- 闇の水晶
    dcry = mat("DarkCrystal", (0.55, 0.25, 0.85), 0.1, emit=(0.6, 0.2, 1.0), emit_strength=3.5)
    drock = mat("DarkRock", (0.18, 0.15, 0.2), 0.95)
    c = proto("RockDarkCrystal")
    mb = MB()
    mb.add('ico', drock, loc=(0, 0, 0.3), r=1.0, sub=2, scale=(1.2, 1.0, 0.5), jitter=0.25, smooth=False, seed=31)
    rng = random.Random(11)
    for k in range(5):
        a = rng.uniform(0, math.tau)
        tilt = rng.uniform(0.0, 0.5)
        ln = rng.uniform(1.2, 2.8)
        d = Vector((math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt)))
        q = Vector((0, 0, 1)).rotation_difference(d)
        base = Vector((math.cos(a) * 0.35, math.sin(a) * 0.35, 0.3))
        mb.add('cyl', dcry, loc=tuple(base + d * ln * 0.4), rot=tuple(q.to_euler()), r1=0.3, r2=0.24, depth=ln * 0.8, seg=5, smooth=False)
        mb.add('cyl', dcry, loc=tuple(base + d * ln * 0.88), rot=tuple(q.to_euler()), r1=0.24, r2=0.0, depth=ln * 0.25, seg=5, smooth=False)
    mb.build("RockDarkCrystal", c)


build_island_props()

# ================================================================== 建物の部品
M = {}


def M_(name, *a, **kw):
    if name not in M:
        M[name] = mat(name, *a, **kw)
    return M[name]


def box_house_flat(mb, w, d, h, wall, trim, door_m, beam=None, rng=None):
    """日干しれんがの家：平屋根・丸みのある角・突き出た梁・のれんの入口"""
    mb.add('cube', wall, loc=(0, 0, h / 2), scale=(w, d, h))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.add('cyl', wall, loc=(sx * w / 2, sy * d / 2, h / 2), r1=0.3, r2=0.3, depth=h, seg=8)
    mb.add('cube', trim, loc=(0, 0, h + 0.15), scale=(w + 0.3, d + 0.3, 0.3))
    mb.add('cube', wall, loc=(0, 0, h + 0.5), scale=(w + 0.1, d + 0.1, 0.5))
    if beam:
        for k in range(int(w // 1.2)):
            x = -w / 2 + 0.6 + k * 1.2
            mb.add('cyl', beam, loc=(x, -d / 2 - 0.3, h - 0.3), rot=(math.pi / 2, 0, 0), r1=0.1, r2=0.1, depth=0.7, seg=6)
    # 入口（布ののれん）と小窓
    mb.add('cube', door_m, loc=(0, -d / 2 - 0.02, 1.15), scale=(1.4, 0.06, 2.3))
    mb.add('cube', trim, loc=(0, -d / 2 - 0.05, 2.4), scale=(1.8, 0.12, 0.2))
    for sx in (-1, 1):
        mb.add('cube', M_("WindowDark", (0.1, 0.08, 0.07), 0.9), loc=(sx * w * 0.3, -d / 2 - 0.02, h * 0.62), scale=(0.6, 0.06, 0.6))


def tent(mb, r, h, cloth, cloth2, pole):
    """ベドウィンの大テント（布は縞模様）"""
    seg = 12
    verts = [(0, 0, h)]
    for k in range(seg):
        a = k / seg * math.tau
        verts.append((math.cos(a) * r, math.sin(a) * r, h * 0.38))
    faces = [(0, 1 + k, 1 + (k + 1) % seg) for k in range(seg)]
    tmp = MB()
    for k in range(seg):
        tmp_m = cloth if k % 2 == 0 else cloth2
        mb.poly([verts[0], verts[1 + k], verts[1 + (k + 1) % seg]], [(0, 1, 2)], tmp_m, smooth=False)
    # 側面の垂れ幕（正面は開く）
    for k in range(seg):
        a0, a1 = k / seg * math.tau, (k + 1) / seg * math.tau
        if abs(math.sin((a0 + a1) / 2) + 1) < 0.5:   # -Y（正面）は開けておく
            continue
        p = [(math.cos(a0) * r, math.sin(a0) * r, h * 0.38), (math.cos(a1) * r, math.sin(a1) * r, h * 0.38),
             (math.cos(a1) * r * 1.02, math.sin(a1) * r * 1.02, 0), (math.cos(a0) * r * 1.02, math.sin(a0) * r * 1.02, 0)]
        mb.poly(p, [(0, 1, 2, 3)], cloth2 if k % 2 else cloth, smooth=False)
    mb.add('cyl', pole, loc=(0, 0, h / 2), r1=0.1, r2=0.08, depth=h, seg=8)
    for k in range(seg):
        a = k / seg * math.tau
        mb.add('cyl', pole, loc=(math.cos(a) * r, math.sin(a) * r, h * 0.19), r1=0.06, r2=0.06, depth=h * 0.38, seg=6)


def stall(mb, w, d, cloth, wood, goods):
    """市場の屋台（布の日よけ・品物）"""
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.add('cyl', wood, loc=(sx * w / 2, sy * d / 2, 1.3), r1=0.07, r2=0.07, depth=2.6, seg=6)
    mb.add('cube', wood, loc=(0, -d / 2 + 0.4, 0.5), scale=(w, 0.8, 1.0))
    mb.add('cube', wood, loc=(0, -d / 2 + 0.4, 1.02), scale=(w + 0.1, 0.9, 0.06))
    mb.poly([(-w / 2 - 0.3, -d / 2 - 0.6, 2.4), (w / 2 + 0.3, -d / 2 - 0.6, 2.4), (w / 2 + 0.3, d / 2 + 0.2, 2.8), (-w / 2 - 0.3, d / 2 + 0.2, 2.8)], [(0, 1, 2, 3)], cloth)
    for k in range(int(w / 0.5)):
        x = -w / 2 + 0.3 + k * 0.5
        g = goods[k % len(goods)]
        mb.add('sphere', g, loc=(x, -d / 2 + 0.35, 1.15), r=0.18, seg=8, rings=5, scale=(1, 1, 0.8))


def lamp_post(isl, mb_name, x, z, light=True):
    mb = MB()
    iron = M_("Iron", (0.12, 0.12, 0.13), 0.5, 0.8)
    glow = M_("WindowLight", (1.0, 0.82, 0.45), 0.5, emit=(1.0, 0.75, 0.35), emit_strength=2.0)
    mb.add('cyl', iron, loc=(0, 0, 1.6), r1=0.08, r2=0.06, depth=3.2, seg=8)
    mb.add('cube', glow, loc=(0, 0, 3.3), scale=(0.35, 0.35, 0.45))
    mb.add('cyl', iron, loc=(0, 0, 3.62), r1=0.3, r2=0.02, depth=0.3, seg=4)
    isl.build(mb, mb_name, x, z)
    if light:
        isl.marker(f"Light_{mb_name}", x, z, y=isl.H(x, z) + 3.3)


def campfire(isl, name, x, z):
    mb = MB()
    stone = M_("CampStone", (0.4, 0.38, 0.36), 0.9)
    wood = M_("WoodDark", (0.25, 0.15, 0.08), 0.8)
    fire = M_("Embers", (1.0, 0.45, 0.1), 0.5, emit=(1.0, 0.4, 0.08), emit_strength=6.0)
    for k in range(9):
        a = k / 9 * math.tau
        mb.add('ico', stone, loc=(math.cos(a) * 0.9, math.sin(a) * 0.9, 0.12), r=0.22, sub=1, jitter=0.05)
    for k in range(4):
        mb.add('cyl', wood, loc=(0, 0, 0.25), rot=(math.pi / 2 - 0.5, 0, k * 0.8), r1=0.08, r2=0.08, depth=1.1, seg=6)
    mb.add('ico', fire, loc=(0, 0, 0.2), r=0.35, sub=1, scale=(1, 1, 0.6))
    isl.build(mb, name, x, z)
    isl.marker(f"Torch_{name}", x, z, y=isl.H(x, z) + 0.3)
    isl.marker(f"Light_{name}", x, z, y=isl.H(x, z) + 1.0)
    isl.marker(f"Smoke_{name}", x, z, y=isl.H(x, z) + 1.2)


def sign_board(isl, sid, x, z, rot, text):
    mb = MB()
    wood = M_("Wood", (0.42, 0.27, 0.14), 0.8)
    mb.add('cyl', wood, loc=(0, 0, 0.8), r1=0.08, r2=0.08, depth=1.6, seg=6)
    mb.add('cube', wood, loc=(0, 0, 1.55), scale=(1.4, 0.1, 0.7))
    isl.build(mb, sid, x, z, rot)
    isl.marker(sid, x, z, rot)
    isl.signs[sid] = text


# ================================================================== 灼砂の島
class Desert(Island):
    TOWN = (-60.0, 55.0)
    POND = (-82.0, 72.0)
    PYR = (72.0, -88.0)
    LAND = (-10.0, 150.0)

    def __init__(self):
        super().__init__("desert", 101)
        self.paths = [
            [self.LAND, (-30, 100), self.TOWN],
            [self.TOWN, (-20, 10), (30, -30), (self.PYR[0], self.PYR[1] + 45)],
        ]
        self.pads += [(self.TOWN[0], self.TOWN[1], 38, 5.0), (self.PYR[0], self.PYR[1], 56, 6.0), (self.LAND[0], self.LAND[1], 18, 3.2)]

    def land(self, x, z):
        base = 3.6 + (fbm(x / 70, z / 70, 3, 1.0) * 0.5 + 0.5) * 3.5
        wind = (x * 0.8 + z * 0.55) / 9.0 + fbm(x / 45, z / 45, 2, 2.0) * 3.0
        dune = (math.sin(wind) * 0.5 + 0.5) ** 2.2 * 5.5
        big = (math.sin((x * 0.4 - z * 0.7) / 28.0 + fbm(x / 90, z / 90, 2, 5.0) * 2) * 0.5 + 0.5) ** 1.6 * 7
        dm = smoothstep(30, 60, math.hypot(x - self.TOWN[0], z - self.TOWN[1])) * smoothstep(45, 75, math.hypot(x - self.PYR[0], z - self.PYR[1]))
        dm *= smoothstep(4, 22, self.path_dist(x, z))
        dm *= smoothstep(20, 60, math.hypot(x - self.LAND[0], z - self.LAND[1]))
        h = base + (dune * 0.8 + big * 0.75) * dm
        # 北西の台地（メサ）
        mesa = smoothstep(0.56, 0.62, fbm(x / 48, z / 48, 3, 3.3) * 0.5 + 0.5) * smoothstep(20, -60, x + z * 0.6) * smoothstep(-10, -70, z)
        h += 15.0 * mesa
        # オアシスの池
        pd = math.hypot(x - self.POND[0], z - self.POND[1]) / 14.0
        h = lerp(h, -2.5, smoothstep(1.0, 0.55, pd))
        return h

    def color(self, x, z, h, s):
        SAND = srgb((0.88, 0.74, 0.5))
        SAND2 = srgb((0.78, 0.6, 0.38))
        ROCK = srgb((0.62, 0.42, 0.26))
        ROCK2 = srgb((0.48, 0.31, 0.19))
        GRASS = srgb((0.36, 0.55, 0.2))
        EARTH = srgb((0.7, 0.56, 0.4))
        SEABED = srgb((0.62, 0.56, 0.38))
        g = fbm(x / 18, z / 18, 3, 7.0) * 0.5 + 0.5
        c = mix(SAND, SAND2, smoothstep(0.35, 0.75, g) * 0.6)
        # 風紋の陰
        c = mix(c, SAND2, smoothstep(0.55, 0.85, nz(x / 3.0, z / 3.0, 4.0) * 0.5 + 0.5) * 0.18)
        c = mix(c, mix(ROCK, ROCK2, g), smoothstep(0.42, 0.8, s))
        c = mix(c, ROCK, smoothstep(13, 17, h) * smoothstep(0.2, 0.5, s + 0.2))
        pd = math.hypot(x - self.POND[0], z - self.POND[1])
        c = mix(c, GRASS, smoothstep(26, 15, pd + nz(x / 4, z / 4, 3.0) * 4) * (1 - smoothstep(1.2, 0.4, h)))
        tw = math.hypot(x - self.TOWN[0], z - self.TOWN[1])
        c = mix(c, EARTH, smoothstep(34, 26, tw) * 0.6)
        c = mix(c, EARTH, smoothstep(4.0, 2.0, self.path_dist(x, z) + nz(x / 3, z / 3, 8.0) * 0.8))
        c = mix(c, SEABED, smoothstep(-0.5, -3.0, h))
        return c

    def build_all(self):
        self.compute()
        self.make_terrain()
        tx, tz = self.TOWN
        adobe = M_("Adobe", (0.84, 0.68, 0.5), 0.95)
        adobe2 = M_("AdobeDark", (0.7, 0.54, 0.38), 0.95)
        beam = M_("WoodDark", (0.25, 0.15, 0.08), 0.8)
        curtain = [M_("ClothRed", (0.7, 0.15, 0.12), 0.9, double=True), M_("ClothBlue", (0.15, 0.3, 0.6), 0.9, double=True), M_("ClothGold", (0.85, 0.6, 0.15), 0.9, double=True)]
        cloth_w = M_("ClothWhite", (0.92, 0.88, 0.8), 0.9, double=True)
        wood = M_("Wood", (0.42, 0.27, 0.14), 0.8)
        goods = [M_("Fruit", (0.95, 0.5, 0.1), 0.6), M_("Melon", (0.4, 0.65, 0.2), 0.6), M_("Pot", (0.62, 0.42, 0.28), 0.7), M_("Spice", (0.8, 0.25, 0.1), 0.8)]
        # 家（日干しれんが）
        houses = [(-20, -16, 0.2, 8, 7, 4.2), (16, -18, -0.3, 9, 7, 4.6), (-24, 14, 2.9, 8, 6, 3.8), (22, 16, 3.4, 9, 7, 4.2), (2, -26, 0.0, 10, 8, 5.2)]
        for k, (dx, dz, rot, w, d, h) in enumerate(houses):
            mb = MB()
            box_house_flat(mb, w, d, h, adobe if k % 2 == 0 else adobe2, adobe2 if k % 2 == 0 else adobe, curtain[k % 3], beam)
            # 屋上の小屋・つぼ
            mb.add('cube', adobe, loc=(w * 0.25, d * 0.2, h + 1.4), scale=(w * 0.35, d * 0.4, 1.6))
            mb.add('sphere', goods[2], loc=(-w * 0.3, d * 0.25, h + 1.0), r=0.35, seg=10, rings=6)
            self.build(mb, f"House{k}", tx + dx, tz + dz, rot)
            self.collider(f"House{k}", tx + dx, tz + dz, w + 0.8, d + 0.8, rot, top=h + 2)
        # 宿屋のテント（大）と道具屋の屋台
        mb = MB()
        tent(mb, 5.5, 5.5, cloth_w, curtain[0], wood)
        for k in range(5):
            mb.add('cube', curtain[k % 3], loc=(-3 + k * 1.5, 1.5, 0.15), scale=(1.3, 2.2, 0.3))
        self.build(mb, "InnTent", tx - 14, tz + 0, 0.0)
        self.collider("InnTent", tx - 14, tz - 0.5, 11, 9.5, 0.0, top=5)
        self.npc("Innkeeper_desert", "Innkeeper", tx - 14, tz + 5.6, 0.0, rng_=4.0)
        self.marker("Camp", tx - 14, tz + 9.5, 0.0)
        mb = MB()
        stall(mb, 4.0, 3.0, curtain[1], wood, goods)
        self.build(mb, "ShopStall", tx + 12, tz + 2, 0.0)
        self.collider("ShopStall", tx + 12, tz + 2.0, 4.6, 3.4, 0.0, top=3)
        self.npc("Merchant_desert", "Merchant", tx + 12, tz + 1.6, 0.0, rng_=4.0)
        for k, (dx, dz) in enumerate(((20, 4), (6, 10))):
            mb = MB()
            stall(mb, 3.2, 2.6, curtain[(k + 2) % 3], wood, goods)
            self.build(mb, f"Stall{k}", tx + dx, tz + dz, 0.4 * k)
            self.collider(f"Stall{k}", tx + dx, tz + dz, 3.6, 2.8, 0.4 * k, top=3)
        # 井戸（オアシスのほとり）
        mb = MB()
        stone = M_("Stone", (0.8, 0.74, 0.62), 0.85)
        mb.add('cyl', stone, loc=(0, 0, 0.5), r1=1.3, r2=1.3, depth=1.0, seg=20)
        mb.add('cyl', M_("WellWater", (0.15, 0.35, 0.55), 0.05), loc=(0, 0, 0.95), r1=1.05, r2=1.05, depth=0.1, seg=20)
        for sx in (-1, 1):
            mb.add('cube', wood, loc=(sx * 1.1, 0, 1.6), scale=(0.15, 0.15, 2.2))
        mb.add('cube', wood, loc=(0, 0, 2.7), scale=(2.6, 0.2, 0.2))
        self.build(mb, "Well", tx - 4, tz + 16)
        self.collider("Well", tx - 4, tz + 16, 2.8, 2.8, top=3)
        campfire(self, "desert_fire", tx + 2, tz + 2)
        for k, (dx, dz) in enumerate(((-8, -8), (10, -9), (-6, 24), (26, 0), (-30, 0))):
            lamp_post(self, f"desert_lamp{k}", tx + dx, tz + dz)
        self.area("Oasis", "オアシスの町 ルミナ", tx, tz, 36, "town")
        self.npc("DesertElder", "Elder", tx + 2, tz - 14, 0.0)
        self.npc("DesertGirl", "Girl", tx - 4, tz + 8, 0.5, wander=True)
        self.npc("DesertTrader", "Villager", tx + 18, tz - 4, -1.2, wander=True)
        self.npc("DesertGuard", "Guard", tx + 6, tz + 30, 0.0)
        # ---- ピラミッド
        px, pz = self.PYR
        st = M_("PyrStone", (0.86, 0.72, 0.5), 0.9)
        st2 = M_("PyrStoneDark", (0.7, 0.56, 0.36), 0.9)
        gold = M_("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
        mb = MB()
        steps = 10
        base = 64.0
        hgt = 40.0
        for k in range(steps):
            w = base * (1 - k / steps)
            mb.add('cube', st if k % 2 == 0 else st2, loc=(0, 0, k * hgt / steps + hgt / steps / 2), scale=(w, w, hgt / steps))
        mb.add('cyl', gold, loc=(0, 0, hgt + 1.6), r1=4.0, r2=0.0, depth=3.6, seg=4, rot=(0, 0, math.pi / 4))
        # 入口（正面＝+z 側）
        dz0 = base / 2
        mb.add('cube', st2, loc=(0, -dz0 - 2.2, 4.0), scale=(10, 4.4, 8))
        mb.add('cube', M_("Abyss", (0, 0, 0), 1.0), loc=(0, -dz0 - 4.45, 2.8), scale=(4.2, 0.2, 5.6))
        mb.add('cube', gold, loc=(0, -dz0 - 4.5, 6.4), scale=(5.2, 0.25, 0.5))
        for sx in (-1, 1):
            mb.add('cube', st, loc=(sx * 3.4, -dz0 - 4.5, 3.4), scale=(1.2, 0.5, 6.8))
            mb.add('cube', M_("Hieroglyph", (0.35, 0.22, 0.12), 0.9), loc=(sx * 3.4, -dz0 - 4.78, 3.6), scale=(0.7, 0.05, 4.8))
        self.build(mb, "Pyramid", px, pz, 0.0)
        self.collider("Pyramid", px, pz, base + 1, base + 1, 0.0, top=hgt)
        self.collider("PyramidPorch1", px - 4.2, pz + dz0 + 2.2, 2, 4.4, 0.0, top=8)
        self.collider("PyramidPorch2", px + 4.2, pz + dz0 + 2.2, 2, 4.4, 0.0, top=8)
        self.marker("Door_pyr1", px, pz + dz0 + 4.2, 0.0)
        self.marker("DoorExit_pyr1", px, pz + dz0 + 9.0, 0.0)
        self.no_scatter.append((px, pz + 50, 20))
        # 参道のオベリスクと山犬の像
        for k in range(4):
            for sx in (-1, 1):
                ox, oz = px + sx * 9, pz + dz0 + 14 + k * 11
                mb = MB()
                mb.add('cube', st2, loc=(0, 0, 0.4), scale=(1.8, 1.8, 0.8))
                mb.add('cyl', st, loc=(0, 0, 4.2), r1=0.75, r2=0.5, depth=6.8, seg=4, rot=(0, 0, math.pi / 4))
                mb.add('cyl', gold, loc=(0, 0, 8.0), r1=0.5, r2=0.0, depth=0.9, seg=4, rot=(0, 0, math.pi / 4))
                self.build(mb, f"Obelisk{k}{sx}", ox, oz)
                self.collider(f"Obelisk{k}{sx}", ox, oz, 2, 2, top=8)
        for sx in (-1, 1):
            mb = MB()
            mb.add('cube', st2, loc=(0, 0, 1.0), scale=(3.0, 5.0, 2.0))
            mb.add('cube', M_("JackalBlack", (0.1, 0.09, 0.1), 0.5), loc=(0, 0.6, 3.4), scale=(1.6, 3.0, 2.6))
            mb.add('cube', M_("JackalBlack", (0.1, 0.09, 0.1), 0.5), loc=(0, -0.9, 5.2), scale=(1.2, 1.6, 1.6))
            mb.add('cube', M_("JackalBlack", (0.1, 0.09, 0.1), 0.5), loc=(0, -2.0, 4.9), scale=(0.6, 1.2, 0.6))
            for ex in (-0.35, 0.35):
                mb.add('cyl', M_("JackalBlack", (0.1, 0.09, 0.1), 0.5), loc=(ex, -0.6, 6.5), r1=0.25, r2=0.0, depth=1.2, seg=4)
            mb.add('cube', gold, loc=(0, -0.2, 4.3), scale=(1.7, 1.2, 0.4))
            self.build(mb, f"Jackal{sx}", px + sx * 9, pz + dz0 + 6, 0.0)
            self.collider(f"Jackal{sx}", px + sx * 9, pz + dz0 + 6, 3.2, 5.2, top=7)
        # ---- 遺跡（折れた柱・砂に埋もれた石像の頭）
        for k in range(14):
            a = k / 14 * math.tau
            cx, cz = -8 + math.cos(a) * 18, -38 + math.sin(a) * 12
            mb = MB()
            hh = self.rng.uniform(1.5, 6.5)
            mb.add('cyl', st, loc=(0, 0, hh / 2), r1=0.9, r2=0.85, depth=hh, seg=12)
            mb.add('cube', st2, loc=(0, 0, 0.3), scale=(2.2, 2.2, 0.6))
            if hh > 5:
                mb.add('cube', st2, loc=(0, 0, hh + 0.3), scale=(2.4, 2.4, 0.6))
            self.build(mb, f"Ruin{k}", cx, cz, a)
            self.collider(f"Ruin{k}", cx, cz, 2.2, 2.2, top=hh)
        mb = MB()
        mb.add('ico', st, loc=(0, 0, 2.5), r=4.5, sub=2, scale=(1, 1.15, 1.05), jitter=0.1)
        mb.add('cube', st2, loc=(0, -3.6, 3.2), scale=(5.5, 1.5, 1.2))
        for sx in (-1, 1):
            mb.add('sphere', M_("Abyss", (0, 0, 0), 1.0), loc=(sx * 1.6, -4.1, 3.0), r=0.6, seg=10, rings=6, scale=(1, 0.4, 0.6))
        mb.add('cube', M_("ClothBlue", (0.15, 0.3, 0.6), 0.9, double=True), loc=(0, 1.0, 5.4), scale=(9.0, 6.0, 0.6))
        self.build(mb, "StatueHead", -92, -58, 0.6, y=self.H(-92, -58) - 1.4)
        self.collider("StatueHead", -92, -58, 9, 9, 0.6, top=6)
        sign_board(self, "SignD1", self.LAND[0] + 6, self.LAND[1] - 8, 0.3, "「 ↑ オアシスの町 ルミナ　　↗ ファラオの ピラミッド 」")
        sign_board(self, "SignD2", -18, 8, 0.8, "「 → ファラオの ピラミッド 」\nすなあらしに ちゅうい。")
        self.marker("Landing", self.LAND[0], self.LAND[1], math.pi)
        self.marker("DragonPark", self.LAND[0] + 12, self.LAND[1] + 4, math.pi)
        # ---- 植物・岩
        tw = lambda x, z: math.hypot(x - tx, z - tz)
        pd = lambda x, z: math.hypot(x - self.POND[0], z - self.POND[1])
        self.scatter([
            ("TreePalm", lambda x, z, h, s: 0.6 * smoothstep(30, 16, pd(x, z)) + 0.05 * smoothstep(40, 30, tw(x, z)), 2.4, (0.8, 1.25)),
            ("Cactus", lambda x, z, h, s: 0.012 * (1 - smoothstep(0.3, 0.6, s)), 1.5, (0.6, 1.3)),
            ("RockDune", lambda x, z, h, s: 0.008 + 0.05 * smoothstep(0.4, 0.8, s), 1.8, (0.6, 1.8)),
        ])
        self.save_meta()


# ================================================================== 氷雪の島
class Ice(Island):
    VIL = (40.0, 78.0)
    PAL = (-38.0, -112.0)
    LAKE = (78.0, -18.0)
    LAND = (-70.0, 150.0)

    def __init__(self):
        super().__init__("ice", 202)
        self.paths = [[self.LAND, (-20, 120), self.VIL], [self.VIL, (10, 20), (-20, -40), (self.PAL[0], self.PAL[1] + 40)]]
        self.pads += [(self.VIL[0], self.VIL[1], 38, 6.0), (self.LAND[0], self.LAND[1], 18, 3.4)]

    def land(self, x, z):
        h = 4.5 + (fbm(x / 60, z / 60, 4, 2.0) * 0.5 + 0.5) * 8
        mtn = smoothstep(-40, -150, z)
        corridor = 1.0 - 0.9 * math.exp(-(poly_dist(x, z, [(10, 20), (-20, -40), (self.PAL[0], self.PAL[1] + 40), self.PAL]) ** 2) / (2 * 24 ** 2))
        h += mtn * (12 + ridged(x / 55, z / 55, 5, 4.0) ** 2 * 55) * corridor
        ld = math.hypot(x - self.LAKE[0], z - self.LAKE[1]) / 32.0 + fbm(x / 30, z / 30, 2, 6.0) * 0.12
        h = lerp(h, -2.5, smoothstep(1.0, 0.6, ld))
        return h

    def build_terrain_pads(self):
        self.pad_here(self.PAL[0], self.PAL[1], 40, 0.0)

    def color(self, x, z, h, s):
        SNOW = srgb((0.93, 0.95, 1.0))
        SNOW2 = srgb((0.8, 0.86, 0.96))
        ROCK = srgb((0.42, 0.44, 0.5))
        ICE = srgb((0.62, 0.8, 0.95))
        EARTH = srgb((0.55, 0.48, 0.4))
        SEABED = srgb((0.45, 0.5, 0.55))
        g = fbm(x / 20, z / 20, 3, 3.0) * 0.5 + 0.5
        c = mix(SNOW, SNOW2, smoothstep(0.4, 0.8, g) * 0.7)
        c = mix(c, ROCK, smoothstep(0.55, 0.95, s))
        ld = math.hypot(x - self.LAKE[0], z - self.LAKE[1])
        c = mix(c, ICE, smoothstep(36, 30, ld))
        c = mix(c, mix(EARTH, SNOW2, 0.4), smoothstep(3.5, 1.8, self.path_dist(x, z) + nz(x / 3, z / 3, 8.0) * 0.8))
        vd = math.hypot(x - self.VIL[0], z - self.VIL[1])
        c = mix(c, mix(EARTH, SNOW, 0.55), smoothstep(30, 22, vd) * 0.5)
        c = mix(c, SEABED, smoothstep(-0.5, -3.0, h) * (1 - smoothstep(36, 30, ld)))
        return c

    def build_all(self):
        self.build_terrain_pads()
        self.compute()
        self.make_terrain()
        vx, vz = self.VIL
        log = M_("LogWood", (0.4, 0.27, 0.17), 0.9)
        log2 = M_("LogWoodDark", (0.28, 0.18, 0.11), 0.9)
        snow = M_("SnowCap", (0.95, 0.97, 1.0), 0.6)
        stone = M_("StoneDark", (0.52, 0.5, 0.48), 0.9)
        win = M_("WindowLight", (1.0, 0.82, 0.45), 0.5, emit=(1.0, 0.75, 0.35), emit_strength=2.0)
        cloth = M_("ClothRed", (0.7, 0.15, 0.12), 0.9, double=True)
        cloth2 = M_("ClothBlue", (0.15, 0.3, 0.6), 0.9, double=True)

        def cabin(mb, w, d, h):
            # 丸太を積んだ壁
            n = int(h / 0.4)
            for k in range(n):
                z = 0.2 + k * 0.4
                for sy in (-1, 1):
                    mb.add('cyl', log if k % 2 else log2, loc=(0, sy * d / 2, z), rot=(0, math.pi / 2, 0), r1=0.22, r2=0.22, depth=w + 0.6, seg=8)
                for sx in (-1, 1):
                    mb.add('cyl', log2 if k % 2 else log, loc=(sx * w / 2, 0, z + 0.2), rot=(math.pi / 2, 0, 0), r1=0.22, r2=0.22, depth=d + 0.6, seg=8)
            mb.add('cube', log2, loc=(0, 0, h / 2), scale=(w - 0.2, d - 0.2, h))
            # 雪の積もった切妻屋根
            rh = 2.6
            for sx in (-1, 1):
                mb.poly([(0, -d / 2 - 0.8, h + rh), (sx * (w / 2 + 0.9), -d / 2 - 0.8, h - 0.2), (sx * (w / 2 + 0.9), d / 2 + 0.8, h - 0.2), (0, d / 2 + 0.8, h + rh)],
                        [(0, 1, 2, 3) if sx > 0 else (3, 2, 1, 0)], log2)
                mb.poly([(0, -d / 2 - 0.85, h + rh + 0.35), (sx * (w / 2 + 1.0), -d / 2 - 0.85, h + 0.1), (sx * (w / 2 + 1.0), d / 2 + 0.85, h + 0.1), (0, d / 2 + 0.85, h + rh + 0.35)],
                        [(0, 1, 2, 3) if sx > 0 else (3, 2, 1, 0)], snow)
            for sy in (-1, 1):
                mb.poly([(-w / 2, sy * d / 2, h - 0.1), (w / 2, sy * d / 2, h - 0.1), (0, sy * d / 2, h + rh)], [(0, 1, 2) if sy < 0 else (2, 1, 0)], log)
            mb.add('cube', stone, loc=(w * 0.3, d * 0.25, h + 1.6), scale=(0.8, 0.8, 3.2))
            mb.add('cube', snow, loc=(w * 0.3, d * 0.25, h + 3.25), scale=(0.95, 0.95, 0.2))
            mb.add('cube', win, loc=(-w * 0.25, -d / 2 - 0.26, h * 0.55), scale=(0.9, 0.06, 0.8))
            mb.add('cube', log2, loc=(w * 0.2, -d / 2 - 0.26, 1.1), scale=(1.1, 0.08, 2.2))

        cabins = [(-18, -12, 0.15, 8, 6, 3.4), (16, -14, -0.2, 8, 6, 3.4), (-22, 14, 2.9, 7, 6, 3.2), (20, 16, 3.3, 8, 6, 3.4)]
        for k, (dx, dz, rot, w, d, h) in enumerate(cabins):
            mb = MB()
            cabin(mb, w, d, h)
            self.build(mb, f"Cabin{k}", vx + dx, vz + dz, rot)
            self.collider(f"Cabin{k}", vx + dx, vz + dz, w + 1.2, d + 1.2, rot, top=h + 3)
            c = Vector((dx, dz))
            self.marker(f"Smoke_ice{k}", vx + dx + math.cos(rot) * w * 0.3, vz + dz + math.sin(rot) * d * 0.25, y=self.H(vx + dx, vz + dz) + h + 3.4)
        # イグルー
        for k, (dx, dz) in enumerate(((-6, 26), (8, 28))):
            mb = MB()
            mb.add('sphere', snow, loc=(0, 0, 0), r=2.6, seg=20, rings=10, scale=(1, 1, 0.85))
            mb.add('cyl', snow, loc=(0, -2.4, 0.6), rot=(math.pi / 2, 0, 0), r1=0.9, r2=0.9, depth=1.6, seg=12)
            mb.add('cube', M_("Abyss", (0, 0, 0), 1.0), loc=(0, -3.2, 0.6), scale=(1.2, 0.05, 1.2))
            for r_ in range(4):
                mb.add('cyl', M_("IceBlock", (0.85, 0.92, 1.0), 0.5), loc=(0, 0, 0.5 + r_ * 0.55), r1=2.6 - r_ * 0.35, r2=2.5 - r_ * 0.35, depth=0.04, seg=20)
            self.build(mb, f"Igloo{k}", vx + dx, vz + dz, 0.3 * k)
            self.collider(f"Igloo{k}", vx + dx, vz + dz, 5, 5, top=2.5)
        # 宿屋・道具屋（屋根つきの屋台）
        mb = MB()
        stall(mb, 5.0, 3.4, cloth, log, [M_("Pot", (0.62, 0.42, 0.28), 0.7), M_("Bread", (0.85, 0.6, 0.3), 0.8)])
        mb.add('cube', snow, loc=(0, 0, 2.95), rot=(-0.12, 0, 0), scale=(5.6, 4.0, 0.15))
        self.build(mb, "IceInn", vx - 10, vz - 2, 0.0)
        self.collider("IceInn", vx - 10, vz - 2.0, 5.6, 3.6, 0.0, top=3)
        self.npc("Innkeeper_ice", "Innkeeper", vx - 10, vz - 2.4, 0.0, rng_=4.0)
        self.marker("Camp", vx - 10, vz + 3.5, 0.0)
        mb = MB()
        stall(mb, 4.4, 3.2, cloth2, log, [M_("Fruit", (0.95, 0.5, 0.1), 0.6), M_("Pot", (0.62, 0.42, 0.28), 0.7)])
        mb.add('cube', snow, loc=(0, 0, 2.95), rot=(-0.12, 0, 0), scale=(5.0, 3.8, 0.15))
        self.build(mb, "IceShop", vx + 10, vz - 2, 0.0)
        self.collider("IceShop", vx + 10, vz - 2.0, 5.0, 3.4, 0.0, top=3)
        self.npc("Merchant_ice", "Merchant", vx + 10, vz - 2.4, 0.0, rng_=4.0)
        campfire(self, "ice_fire", vx, vz + 6)
        for k, (dx, dz) in enumerate(((-8, -10), (9, -11), (-26, 2), (26, 2), (0, 22))):
            lamp_post(self, f"ice_lamp{k}", vx + dx, vz + dz)
        self.area("Silfe", "ゆきの村 シルフェ", vx, vz, 34, "town")
        self.npc("IceElder", "Elder", vx - 2, vz + 12, math.pi)
        self.npc("IceKid", "Girl", vx + 4, vz + 10, 0.0, wander=True)
        self.npc("IceHunter", "Villager", vx + 18, vz + 4, -1.5, wander=True)
        self.npc("IceGuard", "Guard", vx - 4, vz - 30, math.pi)
        # 凍った湖
        mb = MB()
        icesheet = M_("FrozenLake", (0.72, 0.88, 1.0), 0.06, emit=(0.2, 0.35, 0.5), emit_strength=0.4)
        n = 40
        verts = [(0, 0, 0)] + [(math.cos(k / n * math.tau) * 34, math.sin(k / n * math.tau) * 34, 0) for k in range(n)]
        mb.poly(verts, [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)], icesheet)
        self.build(mb, "FrozenLake", self.LAKE[0], self.LAKE[1], y=0.06)
        # ---- 氷の宮殿
        px, pz = self.PAL
        ice = M_("PalaceIce", (0.66, 0.86, 1.0), 0.08, emit=(0.3, 0.6, 1.0), emit_strength=0.7)
        ice2 = M_("PalaceIceDeep", (0.35, 0.6, 0.9), 0.1, emit=(0.15, 0.35, 0.8), emit_strength=0.6)
        mb = MB()
        mb.add('cube', ice2, loc=(0, 0, 1.0), scale=(40, 30, 2.0))
        mb.add('cyl', ice, loc=(0, 6, 10), r1=11, r2=9, depth=16, seg=6)
        mb.add('cyl', ice, loc=(0, 6, 24), r1=9, r2=0.0, depth=14, seg=6)
        for (sx, sy, hh, rr) in ((-15, -6, 22, 4), (15, -6, 22, 4), (-14, 10, 18, 3.5), (14, 10, 18, 3.5), (-6, 16, 26, 3), (6, 16, 26, 3)):
            mb.add('cyl', ice, loc=(sx, sy, hh / 2), r1=rr, r2=rr * 0.85, depth=hh, seg=6)
            mb.add('cyl', ice2, loc=(sx, sy, hh + rr * 1.4), r1=rr * 0.85, r2=0.0, depth=rr * 2.8, seg=6)
        # 正面の門（-y＝ゲームの +z 側）
        mb.add('cube', ice2, loc=(0, -6.5, 5.5), scale=(10, 3, 11))
        mb.add('cube', M_("Abyss", (0, 0, 0), 1.0), loc=(0, -8.05, 3.2), scale=(4.4, 0.1, 6.4))
        mb.add('cyl', ice, loc=(0, -8.1, 6.4), rot=(math.pi / 2, 0, 0), r1=2.2, r2=2.2, depth=0.2, seg=16, scale=(1, 1, 1))
        for sx in (-1, 1):
            for k in range(3):
                mb.add('cyl', ice, loc=(sx * (8 + k * 2.5), -12 - k * 2, 2.5 + k), rot=(0.2 * sx, -0.2, 0), r1=0.9, r2=0.0, depth=5 + k * 2, seg=6)
        self.build(mb, "IcePalace", px, pz, 0.0)
        self.collider("IcePalace", px, pz - 2, 40, 28, 0.0, top=30)
        self.marker("Door_ice1", px, pz + 9.6, 0.0)
        self.marker("DoorExit_ice1", px, pz + 14, 0.0)
        self.no_scatter.append((px, pz + 20, 18))
        sign_board(self, "SignI1", self.LAND[0] + 8, self.LAND[1] - 8, 0.4, "「 → ゆきの村 シルフェ　　↑ こおりの きゅうでん 」")
        sign_board(self, "SignI2", -14, -30, 0.6, "「 ↑ こおりの きゅうでん 」\nこのさき ふぶきに ちゅうい。")
        self.marker("Landing", self.LAND[0], self.LAND[1], math.pi)
        self.marker("DragonPark", self.LAND[0] + 12, self.LAND[1] + 4, math.pi)
        self.scatter([
            ("TreeSnowPine", lambda x, z, h, s: (0.12 + 0.25 * smoothstep(0.5, 0.75, fbm(x / 40, z / 40, 2, 9.0) * 0.5 + 0.5)) * (1 - smoothstep(0.5, 0.8, s)) * (1 - smoothstep(30, 45, h)), 2.4, (0.8, 1.3)),
            ("RockIce", lambda x, z, h, s: 0.01 + 0.03 * smoothstep(20, 40, h), 1.8, (0.6, 1.6)),
            ("RockSnow", lambda x, z, h, s: 0.015 + 0.04 * smoothstep(0.4, 0.8, s), 1.6, (0.6, 1.6)),
        ])
        self.save_meta()


# ================================================================== 炎獄の島
class Volcano(Island):
    CONE = (0.0, -45.0)
    VIL = (-95.0, 92.0)
    ENT = (28.0, 34.0)
    LAND = (95.0, 140.0)
    RIVERS = [[(8, -40), (30, -10), (62, 22), (110, 40), (170, 60)], [(-10, -42), (-40, -5), (-70, 10), (-140, 0)]]

    def __init__(self):
        super().__init__("volcano", 303)
        self.paths = [[self.LAND, (40, 110), (-40, 110), self.VIL], [self.VIL, (-50, 70), (0, 55), self.ENT]]
        self.pads += [(self.VIL[0], self.VIL[1], 34, 5.0), (self.LAND[0], self.LAND[1], 18, 3.4)]

    def cone(self, x, z):
        d = math.hypot(x - self.CONE[0], z - self.CONE[1])
        rough = ridged(x / 30, z / 30, 4, 2.0)
        h = 78 * smoothstep(140, 18, d + fbm(x / 25, z / 25, 3, 5.0) * 10) + rough * 6 * smoothstep(140, 60, d)
        crater = smoothstep(30, 18, d)
        return lerp(h, 46.0, crater)

    def river_dist(self, x, z):
        return min(poly_dist(x, z, r) for r in self.RIVERS)

    def land(self, x, z):
        h = 3.5 + (fbm(x / 55, z / 55, 4, 7.0) * 0.5 + 0.5) * 6
        h = max(h, self.cone(x, z) * 0.7 + h * 0.3)
        rd = self.river_dist(x, z)
        h -= 2.6 * smoothstep(7.0, 2.5, rd) * smoothstep(48, 30, h)
        return h

    def build_terrain_pads(self):
        self.pad_here(self.ENT[0], self.ENT[1], 16, 0.0)

    def color(self, x, z, h, s):
        BAS = srgb((0.075, 0.068, 0.066))
        ASH = srgb((0.2, 0.18, 0.17))
        RED = srgb((0.34, 0.12, 0.07))
        SUL = srgb((0.72, 0.66, 0.3))
        DRY = srgb((0.42, 0.38, 0.22))
        EARTH = srgb((0.38, 0.3, 0.24))
        SEABED = srgb((0.25, 0.22, 0.2))
        g = fbm(x / 16, z / 16, 3, 2.0) * 0.5 + 0.5
        c = mix(ASH, BAS, smoothstep(0.3, 0.7, g))
        d = math.hypot(x - self.CONE[0], z - self.CONE[1])
        c = mix(c, DRY, smoothstep(110, 160, d) * smoothstep(0.55, 0.75, fbm(x / 30, z / 30, 2, 4.0) * 0.5 + 0.5) * 0.7)
        rd = self.river_dist(x, z)
        c = mix(c, RED, smoothstep(12, 5, rd))
        c = mix(c, SUL, smoothstep(40, 30, d) * smoothstep(0.55, 0.8, nz(x / 6, z / 6, 3.0) * 0.5 + 0.5) * 0.7)
        c = mix(c, BAS, smoothstep(0.6, 1.0, s) * 0.6)
        c = mix(c, EARTH, smoothstep(3.6, 1.8, self.path_dist(x, z) + nz(x / 3, z / 3, 8.0) * 0.8))
        c = mix(c, SEABED, smoothstep(-0.5, -3.0, h))
        return c

    def build_all(self):
        self.build_terrain_pads()
        self.compute()
        self.make_terrain()
        lava = M_("LavaFlow", (1.0, 0.36, 0.06), 0.6, emit=(1.0, 0.32, 0.04), emit_strength=2.6)
        # 火口の溶岩湖
        mb = MB()
        n = 40
        verts = [(0, 0, 0)] + [(math.cos(k / n * math.tau) * 24, math.sin(k / n * math.tau) * 24, 0) for k in range(n)]
        mb.poly(verts, [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)], lava)
        self.build(mb, "LavaLake", self.CONE[0], self.CONE[1], y=47.0)
        # 溶岩の川（地形に沿った帯）
        for ri, pts in enumerate(self.RIVERS):
            dense = []
            for i in range(len(pts) - 1):
                a, b = Vector(pts[i]), Vector(pts[i + 1])
                n_ = max(2, int((b - a).length / 2.0))
                for k in range(n_):
                    dense.append(a.lerp(b, k / n_))
            dense.append(Vector(pts[-1]))
            verts, faces = [], []
            for i, p in enumerate(dense):
                q = dense[min(i + 1, len(dense) - 1)] - dense[max(i - 1, 0)]
                q.normalize()
                side = Vector((-q.y, q.x))
                w = 3.0 + nz(p.x / 10, p.y / 10, 2.0) * 0.8
                for sx in (-1, 1):
                    x, z = p.x + side.x * w * sx, p.y + side.y * w * sx
                    hh = min(self.H(x, z), self.H(p.x, p.y)) + 0.35
                    verts.append(B(x, z, hh))
            for i in range(len(dense) - 1):
                a = i * 2
                faces.append((a, a + 1, a + 3, a + 2))
            mb = MB()
            mb.poly(verts, faces, lava, smooth=True)
            mb.build(f"volcano_LavaRiver{ri}", self.C_B)
            for i in range(0, len(dense), 6):
                p = dense[i]
                if self.H(p.x, p.y) > 1:
                    self.marker(f"Light_lava{ri}_{i}", p.x, p.y, y=self.H(p.x, p.y) + 2.0)
        # ---- かじやの里
        vx, vz = self.VIL
        st = M_("SmithStone", (0.36, 0.33, 0.32), 0.9)
        st2 = M_("SmithStoneDark", (0.2, 0.19, 0.19), 0.9)
        slate = M_("RoofSlate", (0.18, 0.16, 0.2), 0.7)
        forge = M_("ForgeGlow", (1.0, 0.45, 0.1), 0.5, emit=(1.0, 0.4, 0.08), emit_strength=5.0)
        iron = M_("Iron", (0.12, 0.12, 0.13), 0.5, 0.8)
        win = M_("WindowLight", (1.0, 0.82, 0.45), 0.5, emit=(1.0, 0.75, 0.35), emit_strength=2.0)

        def stone_house(mb, w, d, h):
            mb.add('cube', st, loc=(0, 0, h / 2), scale=(w, d, h))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    mb.add('cube', st2, loc=(sx * w / 2, sy * d / 2, h / 2), scale=(0.6, 0.6, h + 0.1))
            rh = 2.2
            for sx in (-1, 1):
                mb.poly([(0, -d / 2 - 0.6, h + rh), (sx * (w / 2 + 0.7), -d / 2 - 0.6, h - 0.3), (sx * (w / 2 + 0.7), d / 2 + 0.6, h - 0.3), (0, d / 2 + 0.6, h + rh)],
                        [(0, 1, 2, 3) if sx > 0 else (3, 2, 1, 0)], slate)
            for sy in (-1, 1):
                mb.poly([(-w / 2, sy * d / 2, h), (w / 2, sy * d / 2, h), (0, sy * d / 2, h + rh)], [(0, 1, 2) if sy < 0 else (2, 1, 0)], st)
            mb.add('cube', st2, loc=(w * 0.32, d * 0.2, h + 1.8), scale=(0.9, 0.9, 3.6))
            mb.add('cube', win, loc=(-w * 0.25, -d / 2 - 0.02, h * 0.55), scale=(0.9, 0.06, 0.8))
            mb.add('cube', st2, loc=(w * 0.15, -d / 2 - 0.02, 1.1), scale=(1.2, 0.08, 2.2))
            # 炉（外の小屋）
            mb.add('cube', st2, loc=(-w / 2 - 1.2, -d / 4, 0.9), scale=(1.8, 1.8, 1.8))
            mb.add('cube', forge, loc=(-w / 2 - 1.2, -d / 4 - 0.92, 0.7), scale=(1.0, 0.05, 0.8))
            mb.add('cube', iron, loc=(-w / 2 - 1.0, -d / 2 - 1.2, 0.5), scale=(0.8, 0.4, 0.3))
            mb.add('cube', iron, loc=(-w / 2 - 1.0, -d / 2 - 1.2, 0.25), scale=(0.3, 0.3, 0.5))

        houses = [(-16, -12, 0.1, 8, 7, 4.0), (14, -14, -0.2, 9, 7, 4.2), (-20, 14, 2.8, 8, 6, 3.8), (20, 14, 3.3, 8, 7, 4.0)]
        for k, (dx, dz, rot, w, d, h) in enumerate(houses):
            mb = MB()
            stone_house(mb, w, d, h)
            self.build(mb, f"SmithHouse{k}", vx + dx, vz + dz, rot)
            self.collider(f"SmithHouse{k}", vx + dx, vz + dz, w + 3.5, d + 1.5, rot, top=h + 2)
            self.marker(f"Smoke_volc{k}", vx + dx + math.cos(rot) * w * 0.32, vz + dz + math.sin(rot) * d * 0.2, y=self.H(vx + dx, vz + dz) + h + 3.8)
            self.marker(f"Light_forge{k}", vx + dx - math.cos(rot) * (w / 2 + 1.2), vz + dz - math.sin(rot) * (w / 2 + 1.2), y=self.H(vx + dx, vz + dz) + 1.0)
        cloth = M_("ClothRed", (0.7, 0.15, 0.12), 0.9, double=True)
        mb = MB()
        stall(mb, 5.0, 3.4, cloth, M_("WoodDark", (0.25, 0.15, 0.08), 0.8), [M_("Pot", (0.62, 0.42, 0.28), 0.7)])
        self.build(mb, "VolcInn", vx - 9, vz - 1, 0.0)
        self.collider("VolcInn", vx - 9, vz - 1.0, 5.6, 3.6, top=3)
        self.npc("Innkeeper_volcano", "Innkeeper", vx - 9, vz - 1.4, 0.0, rng_=4.0)
        self.marker("Camp", vx - 9, vz + 4.5, 0.0)
        mb = MB()
        stall(mb, 4.4, 3.2, M_("ClothBlue", (0.15, 0.3, 0.6), 0.9, double=True), M_("WoodDark", (0.25, 0.15, 0.08), 0.8), [iron])
        for k in range(4):
            mb.add('cube', iron, loc=(-1.4 + k * 0.9, -0.95, 1.6), rot=(0.2, 0, 0), scale=(0.08, 0.04, 1.2))
        self.build(mb, "VolcShop", vx + 9, vz - 1, 0.0)
        self.collider("VolcShop", vx + 9, vz - 1.0, 5.0, 3.4, top=3)
        self.npc("Merchant_volcano", "Merchant", vx + 9, vz - 1.4, 0.0, rng_=4.0)
        campfire(self, "volc_fire", vx, vz + 6)
        for k, (dx, dz) in enumerate(((-6, -9), (7, -10), (-24, 0), (24, 0))):
            lamp_post(self, f"volc_lamp{k}", vx + dx, vz + dz)
        self.area("Gold", "かじやの里 ゴルド", vx, vz, 32, "town")
        self.npc("SmithElder", "Elder", vx + 2, vz + 12, math.pi)
        self.npc("SmithBoy", "Villager", vx - 4, vz + 10, 0.0, wander=True)
        self.npc("SmithMaster", "Guard", vx + 16, vz + 4, -1.4)
        # ---- 火口の洞窟（入口）
        ex, ez = self.ENT
        mb = MB()
        for k in range(9):
            a = math.pi * (k / 8)
            mb.add('ico', st2, loc=(math.cos(a) * 5.5, 0, math.sin(a) * 6.0 + 0.5), r=1.8, sub=1, jitter=0.4, smooth=False, seed=k)
        mb.add('cube', M_("Abyss", (0, 0, 0), 1.0), loc=(0, 0.8, 2.8), scale=(7.0, 0.3, 5.8))
        mb.add('cube', forge, loc=(0, 1.2, 0.05), scale=(5.0, 2.0, 0.05))
        for sx in (-1, 1):
            mb.add('cyl', st2, loc=(sx * 6.5, -1.5, 3.5), r1=0.9, r2=0.7, depth=7, seg=6)
            mb.add('cube', forge, loc=(sx * 6.5, -2.3, 4.0), scale=(0.15, 0.1, 3.0))
        self.build(mb, "LavaCaveGate", ex, ez, 0.0)
        self.collider("LavaCaveGateL", ex - 6.2, ez, 3, 3, top=8)
        self.collider("LavaCaveGateR", ex + 6.2, ez, 3, 3, top=8)
        self.collider("LavaCaveBack", ex, ez - 3.0, 12, 2.0, top=8)
        self.marker("Door_lava1", ex, ez + 1.2, 0.0)
        self.marker("DoorExit_lava1", ex, ez + 6.0, 0.0)
        self.marker("Light_lavagate", ex, ez, y=self.H(ex, ez) + 2.5)
        self.no_scatter.append((ex, ez + 8, 12))
        sign_board(self, "SignV1", self.LAND[0] - 8, self.LAND[1] - 8, -0.4, "「 ← かじやの里 ゴルド　　↑ ひのやまの どうくつ 」")
        self.marker("Landing", self.LAND[0], self.LAND[1], math.pi)
        self.marker("DragonPark", self.LAND[0] - 12, self.LAND[1] + 4, math.pi)
        d = lambda x, z: math.hypot(x - self.CONE[0], z - self.CONE[1])
        self.scatter([
            ("TreeDead", lambda x, z, h, s: 0.02 * smoothstep(80, 120, d(x, z)) * (1 - smoothstep(0.4, 0.7, s)), 2.2, (0.8, 1.3)),
            ("RockLava", lambda x, z, h, s: 0.01 + 0.03 * smoothstep(14, 6, self.river_dist(x, z)), 1.8, (0.6, 1.6)),
            ("RockBasalt", lambda x, z, h, s: 0.012 + 0.02 * smoothstep(0.4, 0.8, s), 2.0, (0.7, 1.8)),
        ])
        self.save_meta()


# ================================================================== 闇の島
class Dark(Island):
    CAS = (0.0, -118.0)
    FORT = (45.0, 100.0)
    GRAVE = (-78.0, 10.0)
    LAND = (-40.0, 158.0)

    def __init__(self):
        super().__init__("dark", 404)
        self.paths = [[self.LAND, (0, 130), self.FORT], [self.FORT, (20, 40), (-10, -20), (-6, -70), (self.CAS[0], self.CAS[1] + 38)]]
        self.pads += [(self.FORT[0], self.FORT[1], 34, 6.0), (self.LAND[0], self.LAND[1], 18, 3.4)]

    def land(self, x, z):
        h = 5 + (fbm(x / 50, z / 50, 4, 3.0) * 0.5 + 0.5) * 10
        h += ridged(x / 40, z / 40, 4, 8.0) ** 3 * 18 * smoothstep(60, 140, math.hypot(x, z))
        ch = 22 * smoothstep(70, 35, math.hypot(x - self.CAS[0], z - self.CAS[1]))
        return h + ch

    def build_terrain_pads(self):
        self.pads.append((self.CAS[0], self.CAS[1], 42, self.height_raw(self.CAS[0], self.CAS[1])))

    def color(self, x, z, h, s):
        SOIL = srgb((0.2, 0.17, 0.21))
        DEAD = srgb((0.32, 0.29, 0.22))
        ROCK = srgb((0.27, 0.23, 0.3))
        PURP = srgb((0.3, 0.18, 0.36))
        EARTH = srgb((0.36, 0.32, 0.3))
        SEABED = srgb((0.2, 0.18, 0.2))
        g = fbm(x / 18, z / 18, 3, 4.0) * 0.5 + 0.5
        c = mix(SOIL, DEAD, smoothstep(0.45, 0.75, g) * 0.8)
        c = mix(c, ROCK, smoothstep(0.5, 0.9, s))
        c = mix(c, PURP, smoothstep(50, 30, math.hypot(x - self.CAS[0], z - self.CAS[1])) * 0.6)
        c = mix(c, EARTH, smoothstep(3.6, 1.8, self.path_dist(x, z) + nz(x / 3, z / 3, 8.0) * 0.8))
        c = mix(c, SEABED, smoothstep(-0.5, -3.0, h))
        return c

    def build_all(self):
        self.build_terrain_pads()
        self.compute()
        self.make_terrain()
        fx, fz = self.FORT
        log = M_("LogWood", (0.4, 0.27, 0.17), 0.9)
        log2 = M_("LogWoodDark", (0.28, 0.18, 0.11), 0.9)
        canvas = M_("TentCanvas", (0.62, 0.56, 0.44), 0.9, double=True)
        banner = M_("BannerBlue", (0.15, 0.3, 0.7), 0.8, double=True)
        # 丸太の柵（門は南）
        R = 26
        n = 64
        for k in range(n):
            a = k / n * math.tau
            if abs(math.sin(a) - 1) < 0.08:   # +z（南）は門
                continue
            x, z = fx + math.cos(a) * R, fz + math.sin(a) * R
            mb = MB()
            hh = 4.2 + (k % 2) * 0.4
            mb.add('cyl', log2 if k % 2 else log, loc=(0, 0, hh / 2), r1=0.35, r2=0.32, depth=hh, seg=8)
            mb.add('cyl', log, loc=(0, 0, hh + 0.3), r1=0.32, r2=0.0, depth=0.6, seg=8)
            self.build(mb, f"Palisade{k}", x, z)
            self.collider(f"Palisade{k}", x, z, 0.8, 0.8, top=hh)
        # 見張り台
        mb = MB()
        for sx in (-1, 1):
            for sy in (-1, 1):
                mb.add('cyl', log2, loc=(sx * 1.4, sy * 1.4, 4), r1=0.2, r2=0.2, depth=8, seg=8)
        mb.add('cube', log, loc=(0, 0, 8.1), scale=(3.6, 3.6, 0.3))
        mb.add('cyl', canvas, loc=(0, 0, 9.6), r1=2.8, r2=0.0, depth=2.6, seg=4, rot=(0, 0, math.pi / 4))
        mb.add('cube', banner, loc=(1.9, 0, 6.5), scale=(0.05, 1.2, 2.4))
        self.build(mb, "Watchtower", fx + 18, fz - 12)
        self.collider("Watchtower", fx + 18, fz - 12, 3.6, 3.6, top=8)
        # テント
        for k, (dx, dz, rot) in enumerate(((-12, -10, 0.3), (-14, 6, 1.8), (12, 8, -1.6), (0, -16, 0.0))):
            mb = MB()
            tent(mb, 3.2, 3.6, canvas, log, log2)
            self.build(mb, f"FortTent{k}", fx + dx, fz + dz, rot)
            self.collider(f"FortTent{k}", fx + dx, fz + dz, 5.5, 5.5, rot, top=3.5)
        mb = MB()
        stall(mb, 5.0, 3.4, banner, log2, [M_("Pot", (0.62, 0.42, 0.28), 0.7), M_("Bread", (0.85, 0.6, 0.3), 0.8)])
        self.build(mb, "FortInn", fx - 4, fz + 6, 0.0)
        self.collider("FortInn", fx - 4, fz + 6.0, 5.6, 3.6, top=3)
        self.npc("Innkeeper_dark", "Innkeeper", fx - 4, fz + 5.6, 0.0, rng_=4.0)
        self.marker("Camp", fx - 4, fz + 11.5, 0.0)
        mb = MB()
        stall(mb, 4.4, 3.2, M_("ClothRed", (0.7, 0.15, 0.12), 0.9, double=True), log2, [M_("Iron", (0.12, 0.12, 0.13), 0.5, 0.8)])
        self.build(mb, "FortShop", fx + 6, fz + 6, 0.0)
        self.collider("FortShop", fx + 6, fz + 6.0, 5.0, 3.4, top=3)
        self.npc("Merchant_dark", "Merchant", fx + 6, fz + 5.6, 0.0, rng_=4.0)
        campfire(self, "dark_fire", fx + 1, fz - 4)
        for k, (dx, dz) in enumerate(((-6, 20), (6, 20), (-20, -4), (20, -2))):
            lamp_post(self, f"dark_lamp{k}", fx + dx, fz + dz)
        self.area("Fort", "レジスタンスの砦", fx, fz, 28, "town")
        self.npc("RebelLeader", "Guard", fx + 2, fz - 10, math.pi)
        self.npc("RebelSoldier", "Guard", fx - 6, fz + 22, 0.0)
        self.npc("RebelGirl", "Girl", fx + 8, fz - 2, 0.0, wander=True)
        self.npc("RebelOld", "Elder", fx - 10, fz - 2, 1.2)
        # ---- 混沌の城
        cx, cz = self.CAS
        dst = M_("ChaosStone", (0.22, 0.2, 0.26), 0.85)
        dst2 = M_("ChaosStoneDark", (0.12, 0.1, 0.15), 0.9)
        roof = M_("TowerRoof", (0.28, 0.08, 0.36), 0.5)
        glow = M_("MagicGlow", (0.75, 0.35, 1.0), 0.2, emit=(0.75, 0.30, 1.0), emit_strength=4.0)
        mb = MB()
        mb.add('cube', dst, loc=(0, 4, 9), scale=(26, 20, 18))
        for k in range(13):
            mb.add('cube', dst2, loc=(-12 + k * 2, -6.2, 18.6), scale=(1.0, 1.0, 1.2))
        mb.add('cube', dst, loc=(0, 8, 24), scale=(12, 10, 12))
        mb.add('cyl', roof, loc=(0, 8, 34), r1=8, r2=0.0, depth=10, seg=4, rot=(0, 0, math.pi / 4))
        for (sx, sy) in ((-15, -8), (15, -8), (-15, 16), (15, 16)):
            mb.add('cyl', dst, loc=(sx, sy, 13), r1=4, r2=3.6, depth=26, seg=12)
            mb.add('cyl', roof, loc=(sx, sy, 30), r1=4.6, r2=0.0, depth=8, seg=12)
            for k in range(3):
                mb.add('cube', glow, loc=(sx, sy - 3.65, 8 + k * 6), scale=(0.6, 0.1, 1.6))
        mb.add('cube', dst2, loc=(0, -7, 5), scale=(9, 4, 10))
        mb.add('cube', M_("Abyss", (0, 0, 0), 1.0), loc=(0, -9.05, 3.2), scale=(4.2, 0.1, 6.4))
        mb.add('cube', glow, loc=(0, -9.1, 7.0), scale=(5.0, 0.1, 0.4))
        for k in range(5):
            mb.add('cube', glow, loc=(-8 + k * 4, -6.15, 12), scale=(0.8, 0.1, 2.0))
        self.build(mb, "ChaosCastle", cx, cz, 0.0)
        self.collider("ChaosCastle", cx, cz - 4, 36, 30, 0.0, top=30)
        self.collider("ChaosGateL", cx - 3.5, cz + 7, 2, 4, top=10)
        self.collider("ChaosGateR", cx + 3.5, cz + 7, 2, 4, top=10)
        self.marker("Door_dark1", cx, cz + 10.4, 0.0)
        self.marker("DoorExit_dark1", cx, cz + 15, 0.0)
        self.marker("Light_castle", cx, cz + 12, y=self.H(cx, cz) + 5)
        self.no_scatter.append((cx, cz + 22, 16))
        # 浮かぶ水晶
        for k in range(6):
            a = k / 6 * math.tau
            mb = MB()
            mb.add('cyl', glow, loc=(0, 0, 0), r1=0.9, r2=0.0, depth=2.4, seg=5, smooth=False)
            mb.add('cyl', glow, loc=(0, 0, -1.6), r1=0.9, r2=0.0, depth=0.9, seg=5, rot=(math.pi, 0, 0), smooth=False)
            x, z = cx + math.cos(a) * 30, cz + math.sin(a) * 26
            self.build(mb, f"FloatCrystal{k}", x, z, y=self.H(x, z) + 9 + (k % 2) * 3)
        sign_board(self, "SignK1", self.LAND[0] + 8, self.LAND[1] - 8, 0.3, "「 → レジスタンスの砦　　↑ こんとんの しろ 」")
        sign_board(self, "SignK2", self.GRAVE[0] + 14, self.GRAVE[1] + 14, 0.8, "「 わすれられた ぼち 」\nしずかに ねむらせて あげて。")
        self.marker("Landing", self.LAND[0], self.LAND[1], math.pi)
        self.marker("DragonPark", self.LAND[0] - 12, self.LAND[1] + 4, math.pi)
        gd = lambda x, z: math.hypot(x - self.GRAVE[0], z - self.GRAVE[1])
        self.scatter([
            ("RockGrave", lambda x, z, h, s: 0.5 * smoothstep(24, 10, gd(x, z)), 1.6, (0.8, 1.2)),
            ("TreeDark", lambda x, z, h, s: (0.03 + 0.12 * smoothstep(0.55, 0.75, fbm(x / 35, z / 35, 2, 7.0) * 0.5 + 0.5)) * (1 - smoothstep(0.45, 0.75, s)), 2.4, (0.8, 1.3)),
            ("RockDarkCrystal", lambda x, z, h, s: 0.006 + 0.05 * smoothstep(0.62, 0.8, fbm(x / 30, z / 30, 2, 11.0) * 0.5 + 0.5), 2.0, (0.6, 1.6)),
        ])
        self.save_meta()


for cls in (Desert, Ice, Volcano, Dark):
    isl = cls()
    isl.build_all()

print("islands done")
