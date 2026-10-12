# -*- coding: utf-8 -*-
"""
ひかりの伝説 — モンスター生成（build_world.py → build_characters.py の後に実行）
メタボールで有機的な体を作り、顔・角・翼などを追加する。
各モンスターは Empty "Mon_<名前>" の子に "Mon_<名前>_Body" などの部品を持つ（ゲーム側で部品ごとに動かす）。
座標: Blender、-Y が正面、足元 z=0。
"""
import os, sys, math, random
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\OWNER-1121R\Desktop\クロード\ドラクエ\blender"
sys.path.insert(0, _here)
import importlib, bkit, bmeta
importlib.reload(bkit)
importlib.reload(bmeta)
from bkit import *
from bmeta import CMB, E_ball, E_cap, E_ell, E_dir, E_chain, meta_mesh, decimate, mesh_to_obj, Surface, basis_euler
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion, Euler

COLL = bpy.data.collections["Characters"]
bmeta.set_collection(COLL)
SCENE = bpy.context.scene
_temp_link = COLL.name not in SCENE.collection.children
if _temp_link:
    SCENE.collection.children.link(COLL)

# 既存のモンスターを削除（再実行用）
for ob in list(bpy.data.objects):
    if ob.name.startswith("Mon_"):
        bpy.data.objects.remove(ob)

M_EYEW = mat("EyeWhite", (1.0, 1.0, 1.0), 0.25)
M_PUPIL = mat("Pupil", (0.02, 0.02, 0.03), 0.1)
M_MOUTH = mat("MonMouth", (0.35, 0.04, 0.08), 0.5)
M_TONGUE = mat("MonTongue", (0.95, 0.4, 0.45), 0.4)
M_TOOTH = mat("Tooth", (0.97, 0.95, 0.88), 0.35)
M_CHEEK = mat("Cheek", (1.0, 0.55, 0.5), 0.8)


def eye(mb, surf, x, z, w, h, iris=None, pupil_scale=0.5, look=(0, 0), slit=False, emissive=None, y0=-3.0):
    """表面に埋め込む大きなアニメ目"""
    p, n = surf.ray(Vector((x, y0, z)), Vector((0, 1, 0)))
    if p is None:
        return
    n = (n + Vector((0, -1.0, 0))).normalized()
    e = basis_euler(n)
    sc = mat("EyeGlow_" + str(emissive), emissive, 0.2, emit=emissive, emit_strength=3.0) if emissive else M_EYEW
    mb.add('sphere', sc, loc=p - n * (w * 0.15), rot=e, scale=(w, w * 0.35, h))
    if iris:
        im = mat("Iris_" + str(iris), iris, 0.15)
        mb.add('sphere', im, loc=p + n * (w * 0.04) + Vector((look[0] * w * 0.3, 0, look[1] * h * 0.3)), rot=e, scale=(w * 0.68, w * 0.3, h * 0.72))
    pw = w * pupil_scale * (0.35 if slit else 1.0)
    mb.add('sphere', M_PUPIL, loc=p + n * (w * 0.1) + Vector((look[0] * w * 0.3, 0, look[1] * h * 0.3)), rot=e, scale=(pw, w * 0.28, h * pupil_scale * (1.1 if slit else 1.0)))
    mb.add('sphere', M_EYEW, loc=p + n * (w * 0.2) + Vector((w * 0.25, 0, h * 0.3)), rot=e, scale=(w * 0.16, w * 0.1, w * 0.16))


def surf_point(surf, x, z, y0=-3.0):
    p, n = surf.ray(Vector((x, y0, z)), Vector((0, 1, 0)))
    return p, n


def root(name, x):
    return empty(name, COLL, (x, 0, 0))


# ------------------------------------------------------------------ ぷるりん
def build_purun(x):
    r = root("Mon_Purun", x)
    gel = mat("Gel", (0.36, 0.86, 0.42), 0.08)
    mb = CMB()
    mb.add('sphere', gel, loc=(0, 0, 0), r=0.5, seg=48, rings=32)

    def shape(co):
        t = (co.z + 0.5)
        sq = 1.0 - 0.52 * (t ** 2.3)
        co.x *= sq * 1.18
        co.y *= sq * 1.12
        if co.z < -0.3:
            co.z = -0.3 + (co.z + 0.3) * 0.28
        co.z += 0.4
        return co
    mb.deform(shape)
    body_me = bpy.data.meshes.new("tmp")
    mb.bm.to_mesh(body_me)
    surf = Surface(body_me)
    bpy.data.meshes.remove(body_me)
    for s in (-1, 1):
        eye(mb, surf, s * 0.15, 0.5, 0.105, 0.13, iris=(0.12, 0.08, 0.05), pupil_scale=0.45)
        p, n = surf_point(surf, s * 0.3, 0.33)
        if p:
            mb.add('sphere', M_CHEEK, loc=p - n * 0.01, rot=basis_euler(n), scale=(0.06, 0.012, 0.04))
    p, n = surf_point(surf, 0, 0.3)
    if p:
        e = basis_euler(n)
        mb.add('sphere', M_MOUTH, loc=p - n * 0.02, rot=e, scale=(0.09, 0.03, 0.06))
        mb.add('sphere', M_TONGUE, loc=p - n * 0.005 + Vector((0, 0, -0.025)), rot=e, scale=(0.05, 0.02, 0.028))
    leaf = mat("SproutLeaf", (0.25, 0.62, 0.2), 0.5)
    mb.tube([(0, 0.0, 0.88), (0, 0.01, 0.98), (0.01, 0.0, 1.06)], [0.022, 0.018, 0.015], leaf, seg=8)
    for s in (-1, 1):
        mb.add('sphere', leaf, loc=(s * 0.11, 0.0, 1.1), rot=(0, s * 0.45, 0), scale=(0.13, 0.05, 0.035))
    ob = mb.build("Mon_Purun_Body", COLL, parent=r)
    ob.data.shade_smooth()


# ------------------------------------------------------------------ コウモリン
def build_bat(x):
    r = root("Mon_Bat", x)
    fur = mat("BatFur", (0.42, 0.25, 0.6), 0.75)
    belly = mat("BatBelly", (0.78, 0.62, 0.86), 0.8)
    wingm = mat("BatWing", (0.32, 0.15, 0.45), 0.55, double=True)
    el = [
        E_ell((0, 0, 0), 0.31, 0.29, 0.3),
        E_ell((0, -0.08, -0.12), 0.22, 0.18, 0.18),
        E_ell((0, -0.24, -0.02), 0.07, 0.06, 0.05),
    ]
    for s in (-1, 1):
        el += [E_dir((s * 0.17, 0.0, 0.3), (s * 0.45, 0.1, 1.0), 0.17, 0.075, 0.03),
               E_cap((s * 0.1, 0.0, -0.25), (s * 0.12, -0.03, -0.38), 0.03),
               E_ell((s * 0.12, -0.06, -0.4), 0.04, 0.05, 0.025)]
    me = decimate(meta_mesh("Mon_Bat_Body", el, res=0.012), 6000)
    surf = Surface(me)
    for p in me.polygons:
        c = p.center
        if c.y < -0.12 and c.z < 0.0 and abs(c.x) < 0.17:
            p.material_index = 1
    me.materials.append(fur)
    me.materials.append(belly)
    body = mesh_to_obj(me, "Mon_Bat_Body")
    body.parent = r
    mb = CMB()
    for s in (-1, 1):
        eye(mb, surf, s * 0.115, 0.06, 0.085, 0.1, iris=(1.0, 0.82, 0.15), pupil_scale=0.55, slit=True)
        p, n = surf_point(surf, s * 0.06, -0.1)
        if p:
            mb.add('cyl', M_TOOTH, loc=p + Vector((0, -0.01, -0.035)), rot=(math.pi, 0, 0), r1=0.022, r2=0.0, depth=0.07, seg=6)
        # 耳の内側
        mb.add('sphere', mat("BatEarIn", (0.95, 0.55, 0.7), 0.7), loc=(s * 0.19, -0.035, 0.33), rot=(0, s * 0.42, 0), scale=(0.035, 0.012, 0.11))
    p, n = surf_point(surf, 0, -0.06)
    if p:
        mb.add('sphere', M_MOUTH, loc=p - n * 0.01, rot=basis_euler(n), scale=(0.07, 0.02, 0.025))
    if mb.bm.verts:
        mb.build("Mon_Bat_Face", COLL, parent=body)
    body.location = (0, 0, 1.5)
    # 翼（骨と膜）
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        arm = [Vector((0, 0, 0.05)), Vector((0.32, 0.03, 0.28)), Vector((0.55, 0.05, 0.36))]
        fingers = [Vector((0.95, 0.05, 0.42)), Vector((1.05, 0.05, 0.1)), Vector((0.9, 0.05, -0.18)), Vector((0.55, 0.05, -0.22))]
        pts = [Vector((p.x * sx, p.y, p.z)) for p in arm]
        mb.tube(pts, [0.035, 0.03, 0.022], fur, seg=8)
        hand = pts[-1]
        mem = [Vector((0, 0.02, -0.12))]
        for f in fingers:
            fp = Vector((f.x * sx, f.y, f.z))
            mb.tube([hand, hand.lerp(fp, 0.5), fp], [0.018, 0.012, 0.005], fur, seg=6)
        # 膜（指の間を内側へ湾曲）
        outline = [Vector((0, 0.02, 0.06)), pts[1], hand]
        tips = [Vector((f.x * sx, f.y, f.z)) for f in fingers]
        prev = tips[0]
        outline.append(prev)
        for t in tips[1:]:
            mid = prev.lerp(t, 0.5).lerp(hand, 0.28)
            outline += [mid, t]
            prev = t
        outline.append(Vector((0.18 * sx, 0.02, -0.16)))
        outline.append(Vector((0, 0.02, -0.12)))
        cen = Vector((0.4 * sx, 0.03, 0.1))
        verts = [tuple(cen)] + [tuple(v) for v in outline]
        faces = [(0, i, i + 1) for i in range(1, len(verts) - 1)]
        mb.poly(verts, faces, wingm, smooth=True)
        mb.add('cyl', mat("Claw", (0.9, 0.88, 0.8), 0.4), loc=tuple(hand + Vector((0.03 * sx, 0, 0.06))), rot=(0, -0.3 * sx, 0), r1=0.02, r2=0.0, depth=0.08, seg=6)
        mb.build(f"Mon_Bat_Wing{side}", COLL, loc=(sx * 0.25, 0.04, 1.55), parent=r)


# ------------------------------------------------------------------ おばけキノコ
def build_mushroom(x):
    r = root("Mon_Mushroom", x)
    stem = mat("Stem", (0.97, 0.91, 0.8), 0.75)
    capm = mat("Cap", (0.86, 0.14, 0.1), 0.42)
    gill = mat("Gill", (0.92, 0.82, 0.7), 0.9)
    shoe = mat("MushShoe", (0.45, 0.28, 0.15), 0.7)
    el = [E_ell((0, 0, 0.26), 0.32, 0.3, 0.27), E_ell((0, 0, 0.5), 0.27, 0.26, 0.22), E_ell((0, 0, 0.66), 0.24, 0.23, 0.12)]
    for s in (-1, 1):
        el += [E_cap((s * 0.22, -0.02, 0.4), (s * 0.38, -0.12, 0.28), 0.045), E_ell((s * 0.4, -0.14, 0.26), 0.06, 0.06, 0.06)]
    me = decimate(meta_mesh("Mon_Mushroom_Body", el, res=0.012), 7000)
    surf = Surface(me)
    me.materials.append(stem)
    body = mesh_to_obj(me, "Mon_Mushroom_Body")
    body.parent = r
    mb = CMB()
    # 傘（回転体：ドーム＋反り返ったふち）
    prof = [(0.0, 1.22), (0.18, 1.2), (0.36, 1.14), (0.5, 1.04), (0.6, 0.92), (0.66, 0.8), (0.68, 0.72), (0.64, 0.68)]
    seg = 48
    verts, faces = [], []
    for i, (rr, zz) in enumerate(prof):
        for k in range(seg):
            a = k / seg * math.tau
            wob = 1 + 0.025 * math.sin(a * 5)
            verts.append((math.sin(a) * rr * wob, -math.cos(a) * rr * wob, zz - 0.05))
    for i in range(len(prof) - 1):
        for k in range(seg):
            a = i * seg + k
            b = i * seg + (k + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    mb.poly(verts, faces, capm, smooth=True)
    # 傘の裏（ひだ）
    under = []
    ufaces = []
    for k in range(seg):
        a = k / seg * math.tau
        under.append((math.sin(a) * 0.62, -math.cos(a) * 0.62, 0.62))
    under.append((0, 0, 0.7))
    c = len(under) - 1
    for k in range(seg):
        ufaces.append((c, k, (k + 1) % seg))
    mb.poly(under, ufaces, gill, smooth=False)
    # 斑点
    rng = random.Random(4)
    cap_tmp = CMB()
    cap_tmp.poly(verts, faces, capm, smooth=True)
    tmp_me = bpy.data.meshes.new("tmpcap")
    cap_tmp.bm.to_mesh(tmp_me)
    csurf = Surface(tmp_me)
    bpy.data.meshes.remove(tmp_me)
    for k in range(11):
        a = rng.uniform(0, math.tau)
        el_ = rng.uniform(0.25, 1.15)
        d = Vector((math.sin(a) * math.sin(el_), -math.cos(a) * math.sin(el_), math.cos(el_)))
        p, n = csurf.ray(Vector((0, 0, 0.6)) + d * 2.0, -d)
        if p:
            s_ = rng.uniform(0.06, 0.11)
            mb.add('sphere', M_EYEW, loc=p - n * 0.01, rot=basis_euler(n), scale=(s_, 0.02, s_ * 0.85))
    # 顔
    for s in (-1, 1):
        eye(mb, surf, s * 0.1, 0.44, 0.07, 0.085, iris=(0.15, 0.1, 0.05), pupil_scale=0.5, look=(-s * 0.3, -0.2))
        p, n = surf_point(surf, s * 0.11, 0.535)
        if p:
            mb.add('cube', M_PUPIL, loc=p + n * 0.006, rot=(0, s * 0.45, 0), scale=(0.11, 0.02, 0.022))
        mb.add('sphere', shoe, loc=(s * 0.15, -0.06, 0.04), scale=(0.1, 0.15, 0.06))
    p, n = surf_point(surf, 0, 0.3)
    if p:
        e = basis_euler(n)
        mb.add('sphere', M_MOUTH, loc=p - n * 0.015, rot=e, scale=(0.08, 0.025, 0.04))
        for s in (-1, 1):
            mb.add('cyl', M_TOOTH, loc=p + Vector((s * 0.035, -0.012, 0.025)), rot=(math.pi, 0, 0), r1=0.015, r2=0.0, depth=0.04, seg=5)
    mb.build("Mon_Mushroom_Parts", COLL, parent=body)


# ------------------------------------------------------------------ ゴースト
def build_ghost(x):
    r = root("Mon_Ghost", x)
    gm = mat("Ghost", (0.93, 0.95, 1.0), 0.35, emit=(0.55, 0.7, 1.0), emit_strength=0.35)
    el = [E_ell((0, 0, 0.0), 0.44, 0.42, 0.44), E_ell((0, 0.02, -0.3), 0.42, 0.4, 0.3)]
    for s in (-1, 1):
        el += [E_cap((s * 0.35, -0.05, -0.12), (s * 0.58, -0.18, 0.0), 0.08), E_ball((s * 0.6, -0.2, 0.02), 0.1)]
    me = decimate(meta_mesh("Mon_Ghost_Body", el, res=0.012), 6000)
    surf = Surface(me)
    me.materials.append(gm)
    body = mesh_to_obj(me, "Mon_Ghost_Body")
    body.parent = r
    mb = CMB()
    # 波打つすそ
    prof = [(0.43, -0.25), (0.47, -0.45), (0.52, -0.62), (0.57, -0.78)]
    seg = 56
    verts, faces = [], []
    for i, (rr, zz) in enumerate(prof):
        u = i / (len(prof) - 1)
        for k in range(seg):
            a = k / seg * math.tau
            w = 1 + 0.06 * u * math.sin(a * 3 + 0.5)
            zz2 = zz - u * 0.1 * (0.5 + 0.5 * math.sin(a * 7))
            verts.append((math.sin(a) * rr * w, 0.02 - math.cos(a) * rr * w, zz2))
    for i in range(len(prof) - 1):
        for k in range(seg):
            a = i * seg + k
            b = i * seg + (k + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    mb.poly(verts, faces, mat("GhostSkirt", (0.93, 0.95, 1.0), 0.35, emit=(0.55, 0.7, 1.0), emit_strength=0.35, double=True), smooth=True)
    for s in (-1, 1):
        p, n = surf_point(surf, s * 0.14, 0.06)
        if p:
            mb.add('sphere', M_PUPIL, loc=p - n * 0.01, rot=basis_euler(n), scale=(0.075, 0.03, 0.11))
            mb.add('sphere', M_EYEW, loc=p + n * 0.012 + Vector((0.02, 0, 0.04)), rot=basis_euler(n), scale=(0.018, 0.01, 0.022))
    p, n = surf_point(surf, 0, -0.14)
    if p:
        e = basis_euler(n)
        mb.add('sphere', M_MOUTH, loc=p - n * 0.02, rot=e, scale=(0.09, 0.03, 0.08))
        mb.add('sphere', M_TONGUE, loc=p + Vector((0, -0.01, -0.05)), rot=(0.3, 0, 0), scale=(0.05, 0.03, 0.06))
    mb.build("Mon_Ghost_Parts", COLL, parent=body)
    body.location = (0, 0, 1.6)


# ------------------------------------------------------------------ いわゴーレム
def build_golem(x):
    r = root("Mon_Golem", x)
    gr = mat("GolemRock", (0.55, 0.5, 0.44), 0.95)
    gr2 = mat("GolemRockDark", (0.4, 0.37, 0.34), 0.95)
    ge = mat("GolemEye", (1.0, 0.55, 0.1), 0.3, emit=(1.0, 0.5, 0.05), emit_strength=6.0)
    moss = mat("Moss", (0.34, 0.5, 0.22), 0.95)
    mb = CMB()
    rng = random.Random(9)
    mb.add('ico', gr, loc=(0, 0, 1.55), r=0.85, sub=2, scale=(1.2, 0.9, 1.0), jitter=0.14, smooth=False, seed=2)
    for k in range(9):
        a = rng.uniform(0, math.tau)
        mb.add('ico', gr2 if k % 2 else gr, loc=(math.cos(a) * 0.75, math.sin(a) * 0.55, 1.4 + rng.uniform(-0.4, 0.5)), r=rng.uniform(0.25, 0.4), sub=1, jitter=0.08, smooth=False, seed=k + 30)
    mb.add('ico', gr, loc=(0, -0.08, 2.48), r=0.48, sub=2, scale=(1.0, 0.9, 0.85), jitter=0.08, smooth=False, seed=5)
    mb.add('ico', moss, loc=(0.25, 0.2, 2.22), r=0.42, sub=2, scale=(1.6, 1.2, 0.35), jitter=0.05, smooth=True)
    mb.add('ico', moss, loc=(-0.45, 0.15, 2.0), r=0.32, sub=2, scale=(1.5, 1.2, 0.35), jitter=0.05, smooth=True)
    for s in (-1, 1):
        mb.add('cube', ge, loc=(s * 0.17, -0.47, 2.5), rot=(0, s * 0.2, 0), scale=(0.16, 0.05, 0.08))
        mb.add('ico', gr2, loc=(s * 0.4, 0, 0.45), r=0.4, sub=1, scale=(1, 1, 1.35), jitter=0.06, smooth=False, seed=s + 7)
    # 胸のルーン
    mb.tube([(-0.22, -0.82, 1.82), (0, -0.86, 1.6), (0.22, -0.82, 1.82)], [0.025, 0.025, 0.025], ge, seg=6)
    mb.tube([(0, -0.86, 1.6), (0, -0.82, 1.3)], [0.025, 0.025], ge, seg=6)
    mb.add('ico', ge, loc=(0, -0.86, 1.6), r=0.07, sub=1, smooth=False)
    mb.build("Mon_Golem_Body", COLL, parent=r)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.add('ico', gr, loc=(sx * 0.2, 0, -0.35), r=0.36, sub=1, scale=(1, 1, 1.4), jitter=0.05, smooth=False, seed=11)
        mb.add('ico', gr2, loc=(sx * 0.25, -0.05, -1.0), r=0.44, sub=1, jitter=0.06, smooth=False, seed=13)
        for k in range(3):
            mb.add('ico', gr, loc=(sx * (0.15 + k * 0.1), -0.3, -1.3), r=0.12, sub=1, smooth=False, seed=k)
        mb.build(f"Mon_Golem_Arm{side}", COLL, loc=(sx * 0.98, 0, 2.0), parent=r)


# ------------------------------------------------------------------ 魔竜
def build_dragon(x):
    r = root("Mon_Dragon", x)
    sc = mat("DragonScale", (0.27, 0.11, 0.38), 0.42, 0.1)
    scd = mat("DragonScaleDark", (0.15, 0.06, 0.22), 0.45, 0.1)
    belly = mat("DragonBelly", (0.8, 0.62, 0.38), 0.6)
    horn = mat("Horn", (0.93, 0.89, 0.78), 0.45)
    deye = (1.0, 0.2, 0.08)
    wing = mat("DragonWing", (0.48, 0.12, 0.26), 0.6, double=True)
    el = [
        E_ell((0, 0.35, 2.2), 1.0, 1.45, 0.92),
        E_ell((0, -0.45, 2.45), 0.92, 0.85, 0.98),
        E_ell((0, -0.1, 1.75), 0.75, 1.1, 0.55),
    ]
    neck = [Vector((0, -0.75, 2.85)), Vector((0, -1.15, 3.4)), Vector((0, -1.42, 3.95)), Vector((0, -1.58, 4.45)), Vector((0, -1.62, 4.8))]
    el += E_chain(neck, [0.62, 0.52, 0.45, 0.4, 0.38])
    tail = []
    for i in range(14):
        t = i / 13
        tail.append(Vector((math.sin(t * 3.0) * 0.6, 1.5 + t * 4.4, 2.0 - math.sin(t * 2.3) * 1.55 + t * 0.55)))
    tr = [0.6 * (1 - t) ** 1.15 + 0.06 for t in [i / 13 for i in range(14)]]
    el += E_chain(tail, tr)
    for s in (-1, 1):
        # 前脚
        sh = Vector((s * 0.85, -0.6, 2.05))
        elb = Vector((s * 1.05, -0.85, 1.15))
        wr = Vector((s * 1.02, -0.95, 0.28))
        el += [E_ell(sh, 0.45, 0.5, 0.6), E_cap(sh, elb, 0.33), E_cap(elb, wr, 0.24), E_ball(elb, 0.3),
               E_ell(wr + Vector((0, -0.16, -0.14)), 0.26, 0.36, 0.14)]
        # 後脚
        th = Vector((s * 0.88, 1.0, 1.95))
        kn = Vector((s * 1.0, 0.6, 1.05))
        hk = Vector((s * 1.0, 1.2, 0.5))
        ft = Vector((s * 1.0, 0.95, 0.12))
        el += [E_ell(th, 0.52, 0.78, 0.78), E_cap(th, kn, 0.4), E_cap(kn, hk, 0.27), E_cap(hk, ft, 0.22),
               E_ell(ft + Vector((0, -0.18, 0)), 0.28, 0.4, 0.14)]
    me = decimate(meta_mesh("Mon_Dragon_Body", el, res=0.035), 26000)
    me.materials.append(sc)
    me.materials.append(belly)
    me.materials.append(scd)
    for p in me.polygons:
        c, n = p.center, p.normal
        if abs(c.x) < 0.62 and n.y < -0.25 and n.z < 0.55 and c.z > 1.0 and c.y < 1.2:
            p.material_index = 1
        elif n.z > 0.75 and abs(c.x) < 0.45:
            p.material_index = 2
    body = mesh_to_obj(me, "Mon_Dragon_Body")
    body.parent = r
    mb = CMB()
    # 腹の横じま（鱗の段）
    for i in range(9):
        t = i / 8
        p = Vector((0, -0.95 - t * 0.55, 1.85 + t * 2.2))
        mb.add('cyl', mat("BellyLine", (0.55, 0.38, 0.2), 0.7), loc=tuple(p), rot=(1.2 - t * 0.6, 0, 0), r1=0.5 - t * 0.2, r2=0.5 - t * 0.2, depth=0.025, seg=24, scale=(1, 0.55, 1))
    # 背中のトゲ
    spine = [Vector((0, 0.8 - i * 0.42, 3.1 + max(0, -i + 2) * -0.05)) for i in range(6)]
    for i, p in enumerate(spine):
        mb.add('cyl', horn, loc=tuple(p + Vector((0, 0, 0.12))), rot=(0.35, 0, 0), r1=0.17 - i * 0.012, r2=0.0, depth=0.6, seg=6, scale=(0.4, 1, 1))
    for i in range(1, 12, 2):
        p = tail[i]
        mb.add('cyl', horn, loc=tuple(p + Vector((0, 0, tr[i] + 0.1))), rot=(0.5, 0, 0), r1=tr[i] * 0.45, r2=0.0, depth=0.42, seg=6, scale=(0.4, 1, 1))
    tp = tail[-1]
    mb.add('cyl', horn, loc=tuple(tp + Vector((0, 0.3, 0))), rot=(-math.pi / 2, 0, 0), r1=0.3, r2=0.0, depth=0.7, seg=4, scale=(1, 0.3, 1))
    # 爪
    for s in (-1, 1):
        for (fx, fy) in ((1.02, -1.3), (1.0, 0.58)):
            for k in (-1, 0, 1):
                mb.add('cyl', horn, loc=(s * fx + k * 0.13, fy, 0.08), rot=(math.pi / 2 + 0.4, 0, k * 0.25), r1=0.07, r2=0.0, depth=0.3, seg=6)
    mb.build("Mon_Dragon_Spikes", COLL, parent=body)

    # 頭（首の先が原点）
    hel = [
        E_ell((0, 0.02, 0.06), 0.42, 0.5, 0.36),
        E_ell((0, -0.62, -0.06), 0.3, 0.52, 0.22),
        E_ell((0, -0.98, -0.04), 0.22, 0.2, 0.16),
        E_ell((0, -0.5, -0.3), 0.25, 0.48, 0.11),
        E_ell((0, 0.3, -0.15), 0.38, 0.3, 0.35),
    ]
    for s in (-1, 1):
        hel += [E_ell((s * 0.24, -0.28, 0.22), 0.13, 0.25, 0.08), E_ell((s * 0.33, 0.05, -0.12), 0.14, 0.2, 0.16)]
    hme = decimate(meta_mesh("Mon_Dragon_Head", hel, res=0.02), 9000)
    hme.materials.append(sc)
    hme.materials.append(belly)
    for p in hme.polygons:
        if p.center.z < -0.3 and p.normal.z < -0.3:
            p.material_index = 1
    head = mesh_to_obj(hme, "Mon_Dragon_Head")
    head.parent = r
    hsurf = Surface(hme)
    mb = CMB()
    for s in (-1, 1):
        # 角（湾曲したチューブ）
        mb.tube([(s * 0.26, 0.2, 0.32), (s * 0.42, 0.55, 0.55), (s * 0.5, 0.95, 0.6), (s * 0.48, 1.25, 0.48)], [0.12, 0.09, 0.05, 0.01], horn, seg=10)
        mb.tube([(s * 0.38, 0.0, 0.05), (s * 0.62, 0.2, 0.08), (s * 0.78, 0.38, 0.0)], [0.06, 0.04, 0.008], horn, seg=8)
        # 目
        p, n = hsurf.ray(Vector((s * 1.5, -0.32, 0.14)), Vector((-s, 0.35, 0)))
        if p:
            e = basis_euler(n)
            mb.add('sphere', mat("DragonEye", (1.0, 0.25, 0.08), 0.15, emit=deye, emit_strength=8.0), loc=p - n * 0.01, rot=e, scale=(0.1, 0.03, 0.06))
            mb.add('sphere', M_PUPIL, loc=p + n * 0.005, rot=e, scale=(0.018, 0.02, 0.055))
        # 牙
        for k in range(5):
            yy = -0.95 + k * 0.17
            mb.add('cyl', M_TOOTH, loc=(s * (0.17 + k * 0.012), yy, -0.2), rot=(math.pi, 0, 0), r1=0.03, r2=0.0, depth=0.12 + (0.06 if k == 1 else 0), seg=5)
            mb.add('cyl', M_TOOTH, loc=(s * (0.15 + k * 0.012), yy + 0.06, -0.33), rot=(0, 0, 0), r1=0.026, r2=0.0, depth=0.09, seg=5)
        mb.add('sphere', M_PUPIL, loc=(s * 0.08, -1.13, 0.02), scale=(0.03, 0.02, 0.022))
    mb.add('sphere', mat("DragonMouth", (0.45, 0.04, 0.08), 0.5), loc=(0, -0.55, -0.24), scale=(0.2, 0.44, 0.06))
    mb.build("Mon_Dragon_HeadParts", COLL, parent=head)
    head.location = (0, -1.62, 4.85)

    # 翼
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        shoulder = Vector((0, 0, 0))
        elbow = Vector((1.3 * sx, 0.35, 1.1))
        wrist = Vector((2.4 * sx, 0.5, 1.7))
        mb.tube([shoulder, elbow, wrist], [0.16, 0.11, 0.08], sc, seg=10)
        fingers = [Vector((3.9 * sx, 0.6, 1.4)), Vector((4.2 * sx, 0.7, 0.4)), Vector((3.6 * sx, 0.7, -0.6)), Vector((2.5 * sx, 0.6, -1.1))]
        for f in fingers:
            mb.tube([wrist, wrist.lerp(f, 0.55) + Vector((0, 0, 0.08)), f], [0.07, 0.05, 0.015], sc, seg=8)
        mb.add('cyl', horn, loc=tuple(wrist + Vector((0, 0, 0.18))), rot=(0, -0.4 * sx, 0), r1=0.06, r2=0.0, depth=0.3, seg=6)
        outline = [Vector((0, 0.1, -0.5)), shoulder, elbow, wrist, fingers[0]]
        prev = fingers[0]
        for f in fingers[1:]:
            outline += [prev.lerp(f, 0.5).lerp(wrist, 0.22), f]
            prev = f
        outline += [Vector((1.0 * sx, 0.3, -0.9)), Vector((0.3 * sx, 0.15, -0.8))]
        cen = Vector((1.8 * sx, 0.4, 0.4))
        verts = [tuple(cen)] + [tuple(v) for v in outline]
        faces = [(0, i, i + 1) for i in range(1, len(verts) - 1)]
        mb.poly(verts, faces, wing, smooth=True)
        mb.build(f"Mon_Dragon_Wing{side}", COLL, loc=(sx * 0.7, 0.2, 3.15), parent=r)


build_purun(0.0)
build_bat(2.5)
build_mushroom(5.0)
build_ghost(7.5)
build_golem(10.5)
build_dragon(16.0)

if _temp_link:
    SCENE.collection.children.unlink(COLL)
print("monsters done")
