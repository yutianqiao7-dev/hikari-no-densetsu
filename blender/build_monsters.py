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
    # 背中のトゲ（乗るときは鞍に替えるので別の部品）
    smb = CMB()
    spine = [Vector((0, 0.8 - i * 0.42, 3.1 + max(0, -i + 2) * -0.05)) for i in range(6)]
    for i, p in enumerate(spine):
        smb.add('cyl', horn, loc=tuple(p + Vector((0, 0, 0.12))), rot=(0.35, 0, 0), r1=0.17 - i * 0.012, r2=0.0, depth=0.6, seg=6, scale=(0.4, 1, 1))
    smb.build("Mon_Dragon_BackSpikes", COLL, parent=body)
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

    # 鞍（第二部で竜に乗るとき）：背中の形に沿わせた革の座面・布・金の縁取り・腹帯
    dsurf = Surface(me)
    leather = mat("SaddleLeather", (0.34, 0.19, 0.09), 0.55)
    cloth = mat("SaddleCloth", (0.55, 0.07, 0.1), 0.85, double=True)
    trim = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    ys = [-1.35 + k * 0.15 for k in range(18)]
    top = []
    for y in ys:
        hp, hn = dsurf.ray(Vector((0, y, 9)), Vector((0, 0, -1)))
        top.append(hp if hp else Vector((0, y, 3.2)))
    mb = CMB()
    mb.tube([t + Vector((0, 0, 0.07)) for t in top], [0.48] * len(top), leather, seg=18, flat=0.28)
    for sx in (-1, 1):
        verts, faces = [], []
        for k, t in enumerate(top):
            verts.append((sx * 0.42, t.y, t.z + 0.04))
            verts.append((sx * 0.92, t.y, t.z - 0.75))
        for k in range(len(top) - 1):
            a_ = k * 2
            faces.append((a_, a_ + 2, a_ + 3, a_ + 1) if sx > 0 else (a_, a_ + 1, a_ + 3, a_ + 2))
        mb.poly(verts, faces, cloth, smooth=True)
        mb.tube([Vector((sx * 0.93, t.y, t.z - 0.77)) for t in top], [0.03] * len(top), trim, seg=6)
    # 腹帯
    for yb in (-0.6, 0.55):
        ring = []
        for k in range(25):
            a_ = k / 24 * math.tau
            d = Vector((math.sin(a_), 0, math.cos(a_)))
            hp, hn = dsurf.ray(Vector((0, yb, 2.3)) + d * 3, -d)
            if hp:
                ring.append(hp + d * 0.04)
        if len(ring) > 4:
            mb.tube(ring, [0.05] * len(ring), leather, seg=6, flat=0.4)
    # 前の取っ手
    t0 = top[1]
    mb.tube([t0 + Vector((0, 0, 0.1)), t0 + Vector((0, -0.05, 0.45)), t0 + Vector((0, -0.18, 0.55))], [0.06, 0.05, 0.05], trim, seg=8)
    mb.build("Mon_Dragon_Saddle", COLL, parent=body)
    seat = []
    for y in (-0.95, -0.38, 0.2, 0.78):
        hp, hn = dsurf.ray(Vector((0, y, 9)), Vector((0, 0, -1)))
        seat.append(round((hp.z if hp else 3.2) + 0.07 + 0.48 * 0.28, 3))
    print("DRAGON SEATS (game y)", seat)

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


# ------------------------------------------------------------------ 共通：メタボールの部品（ピボット基準）
def meta_part(name, el, mats, res=0.012, faces=4000, assign=None, parent=None, loc=(0, 0, 0)):
    me = decimate(meta_mesh(name, el, res=res), faces)
    for m in mats:
        me.materials.append(m)
    if assign:
        for p in me.polygons:
            p.material_index = assign(p.center, p.normal)
    ob = mesh_to_obj(me, name)
    ob.parent = parent
    ob.location = loc
    return ob, me


M_CLAW = mat("MonClaw", (0.92, 0.9, 0.82), 0.4)


def cone_to(mb, m, base, d, r, length, seg=6):
    """base から方向 d へ伸びる円すい（爪・トゲ・牙）"""
    d = Vector(d).normalized()
    q = Vector((0, 0, 1)).rotation_difference(d)
    mb.add('cyl', m, loc=tuple(Vector(base) + d * (length * 0.5)), rot=tuple(q.to_euler()), r1=r, r2=0.0, depth=length, seg=seg)


# ------------------------------------------------------------------ キバウルフ
def build_wolf(x):
    r = root("Mon_Wolf", x)
    fur = mat("WolfFur", (0.42, 0.38, 0.35), 0.85)
    furl = mat("WolfFurLight", (0.86, 0.81, 0.73), 0.85)
    furd = mat("WolfFurDark", (0.22, 0.2, 0.19), 0.85)
    el = [
        E_ell((0, -0.3, 0.86), 0.27, 0.36, 0.3),
        E_ell((0, 0.12, 0.85), 0.21, 0.4, 0.23),
        E_ell((0, 0.5, 0.87), 0.24, 0.26, 0.26),
        E_ell((0, -0.5, 1.0), 0.29, 0.22, 0.3),
        E_cap((0, -0.55, 1.0), (0, -0.74, 1.2), 0.19),
        E_dir((0, -0.46, 0.66), (0, -0.25, -1), 0.13, 0.13, 0.08),
    ]
    # 逆立った背中の毛
    for i in range(6):
        el.append(E_dir((0, -0.55 + i * 0.15, 1.11 - 0.025 * i), (0, 0.8, 1), 0.09, 0.06, 0.035))
    # 胸の飾り毛
    for s in (-1, 1):
        el.append(E_dir((s * 0.18, -0.55, 0.85), (s * 0.5, -0.4, -1), 0.12, 0.07, 0.05))

    def a_body(c, n):
        if n.z < -0.35 or (c.y < -0.45 and n.y < -0.4 and c.z < 1.0):
            return 1
        if c.z > 1.05 and n.z > 0.45:
            return 2
        return 0
    body, _ = meta_part("Mon_Wolf_Body", el, [fur, furl, furd], res=0.013, faces=9000, assign=a_body, parent=r)

    # 頭（首の付け根がピボット）
    hel = [
        E_ell((0, -0.02, 0.04), 0.17, 0.19, 0.16),
        E_ell((0, -0.22, -0.01), 0.12, 0.15, 0.11),
        E_ell((0, -0.39, -0.03), 0.07, 0.12, 0.07),
        E_ell((0, -0.3, -0.1), 0.07, 0.13, 0.04),
    ]
    for s in (-1, 1):
        hel += [E_ell((s * 0.13, 0.02, -0.04), 0.08, 0.1, 0.1),
                E_dir((s * 0.1, 0.04, 0.17), (s * 0.35, 0.15, 1), 0.13, 0.065, 0.025)]

    def a_head(c, n):
        if c.z > 0.2:
            return 2
        if c.z < -0.06 and c.y < -0.12:
            return 1
        return 0
    head, hme = meta_part("Mon_Wolf_Head", hel, [fur, furl, furd], res=0.008, faces=5000, assign=a_head, parent=body, loc=(0, -0.8, 1.22))
    hs = Surface(hme)
    mb = CMB()
    for s in (-1, 1):
        eye(mb, hs, s * 0.085, 0.1, 0.045, 0.034, iris=(1.0, 0.72, 0.1), pupil_scale=0.55, slit=True)
        p, n = surf_point(hs, s * 0.09, 0.15)
        if p:
            mb.add('cube', furd, loc=p + n * 0.01, rot=(0, s * 0.45, 0), scale=(0.07, 0.02, 0.016))
        mb.add('sphere', mat("WolfEarIn", (0.35, 0.22, 0.22), 0.8), loc=(s * 0.135, 0.0, 0.25), rot=(-0.14, s * 0.33, 0), scale=(0.035, 0.012, 0.08))
        mb.add('cyl', M_TOOTH, loc=(s * 0.045, -0.43, -0.085), rot=(math.pi, 0, 0), r1=0.014, r2=0.0, depth=0.05, seg=5)
        mb.add('cyl', M_TOOTH, loc=(s * 0.04, -0.41, -0.115), rot=(0, 0, 0), r1=0.011, r2=0.0, depth=0.035, seg=5)
    p, n = hs.ray(Vector((0, -2, -0.01)), Vector((0, 1, 0)))
    if p:
        mb.add('sphere', M_PUPIL, loc=p + n * 0.01, scale=(0.042, 0.03, 0.03))
    mb.add('sphere', M_MOUTH, loc=(0, -0.36, -0.075), scale=(0.06, 0.1, 0.012))
    mb.build("Mon_Wolf_HeadParts", COLL, parent=head)

    # 脚（腰・肩がピボット）
    def leg(name, pivot, front):
        if front:
            lel = [E_ell((0, 0, -0.05), 0.1, 0.13, 0.17), E_cap((0, 0, -0.1), (0, 0.02, -0.42), 0.075),
                   E_cap((0, 0.02, -0.42), (0, -0.01, -0.74), 0.05), E_ell((0, -0.06, -0.78), 0.065, 0.1, 0.045)]
        else:
            lel = [E_ell((0, 0.02, -0.1), 0.11, 0.17, 0.22), E_cap((0, 0.04, -0.15), (0, 0.16, -0.45), 0.075),
                   E_cap((0, 0.16, -0.45), (0, 0.08, -0.74), 0.045), E_ell((0, 0.02, -0.78), 0.065, 0.1, 0.045)]
        ob, _ = meta_part(name, lel, [fur, furd], res=0.008, faces=2500, assign=lambda c, n: 1 if c.z < -0.55 else 0, parent=r, loc=pivot)
        mb = CMB()
        fy = -0.15 if front else -0.07
        for k in (-1, 0, 1):
            cone_to(mb, M_CLAW, (k * 0.03, fy, -0.79), (k * 0.2, -1, -0.5), 0.012, 0.05)
        mb.build(name + "Claws", COLL, parent=ob)
    leg("Mon_Wolf_LegFL", (0.15, -0.42, 0.83), True)
    leg("Mon_Wolf_LegFR", (-0.15, -0.42, 0.83), True)
    leg("Mon_Wolf_LegBL", (0.15, 0.5, 0.83), False)
    leg("Mon_Wolf_LegBR", (-0.15, 0.5, 0.83), False)

    tpts = [Vector(v) for v in ((0, 0, 0), (0, 0.18, 0.02), (0, 0.36, -0.08), (0, 0.52, -0.25), (0, 0.6, -0.44))]
    meta_part("Mon_Wolf_Tail", E_chain(tpts, [0.06, 0.1, 0.12, 0.1, 0.03]), [fur, furl], res=0.01, faces=2500,
              assign=lambda c, n: 1 if c.z < -0.28 else 0, parent=body, loc=(0, 0.7, 0.98))


# ------------------------------------------------------------------ ハサミガニ
def build_crab(x):
    r = root("Mon_Crab", x)
    shell = mat("CrabShell", (0.86, 0.3, 0.15), 0.38)
    shelld = mat("CrabShellDark", (0.55, 0.13, 0.07), 0.45)
    belly = mat("CrabBelly", (0.96, 0.86, 0.7), 0.6)
    el = [E_ell((0, 0, 0.5), 0.46, 0.34, 0.2), E_ell((0, 0.02, 0.42), 0.4, 0.3, 0.14), E_ell((0, -0.04, 0.6), 0.3, 0.24, 0.08)]
    for bx, by in ((-0.2, -0.04), (0.2, -0.04), (0, 0.1), (-0.13, 0.16), (0.13, 0.16)):
        el.append(E_ball((bx, by, 0.64), 0.075))
    for s in (-1, 1):
        el += [E_dir((s * 0.4, -0.18, 0.52), (s, -0.6, 0.1), 0.09, 0.035, 0.035),
               E_dir((s * 0.27, -0.28, 0.52), (s * 0.5, -1, 0.15), 0.07, 0.03, 0.03)]

    def a_body(c, n):
        if n.z < -0.3:
            return 1
        return 0
    body, me = meta_part("Mon_Crab_Body", el, [shell, belly, shelld], res=0.012, faces=7000, assign=a_body, parent=r)
    mb = CMB()
    for s in (-1, 1):
        mb.tube([(s * 0.09, -0.22, 0.6), (s * 0.11, -0.27, 0.72), (s * 0.12, -0.29, 0.8)], [0.026, 0.022, 0.02], shell, seg=8)
        mb.add('sphere', M_EYEW, loc=(s * 0.12, -0.29, 0.84), scale=(0.055, 0.05, 0.055))
        mb.add('sphere', M_PUPIL, loc=(s * 0.12, -0.335, 0.845), scale=(0.03, 0.015, 0.034))
        mb.add('sphere', M_EYEW, loc=(s * 0.12 + 0.012, -0.35, 0.86), scale=(0.01, 0.006, 0.01))
    mb.add('sphere', M_MOUTH, loc=(0, -0.3, 0.43), scale=(0.08, 0.03, 0.03))
    for bx, bz, br in ((0.05, 0.46, 0.022), (0.08, 0.5, 0.015), (0.06, 0.54, 0.01)):
        mb.add('sphere', mat("Bubble", (0.85, 0.95, 1.0), 0.05), loc=(bx, -0.33, bz), scale=(br, br, br))
    mb.build("Mon_Crab_Face", COLL, parent=body)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        for k in range(3):
            yk = (k - 1) * 0.16
            mb.tube([(0, yk, 0), (sx * 0.25, yk - 0.02, 0.16), (sx * 0.46, yk - 0.03, -0.04), (sx * 0.53, yk - 0.04, -0.43)],
                    [0.05, 0.045, 0.035, 0.012], shell, seg=8)
            mb.add('sphere', shelld, loc=(sx * 0.25, yk - 0.02, 0.16), scale=(0.05, 0.05, 0.05))
        mb.build(f"Mon_Crab_Legs{side}", COLL, loc=(sx * 0.34, 0.1, 0.45), parent=r)
        f = 1.2 if side == "L" else 0.95
        V_ = lambda a, b, c: Vector((sx * a * f, b * f, c * f))
        cel = E_chain([V_(0, 0, 0), V_(0.2, -0.12, 0.05), V_(0.3, -0.3, 0.12)], [0.06 * f, 0.055 * f, 0.06 * f])
        cel += [E_ell(V_(0.33, -0.46, 0.16), 0.11 * f, 0.18 * f, 0.1 * f)]
        cel += E_chain([V_(0.32, -0.6, 0.12), V_(0.3, -0.76, 0.11), V_(0.24, -0.88, 0.15)], [0.055 * f, 0.04 * f, 0.01])
        claw, _ = meta_part(f"Mon_Crab_Claw{side}", cel, [shell, shelld], res=0.008, faces=4000,
                            assign=lambda c, n: 1 if c.y < -0.6 * f else 0, parent=r, loc=(sx * 0.32, -0.2, 0.48))
        hinge = V_(0.33, -0.55, 0.22)
        pel = E_chain([Vector((0, 0, 0)), V_(-0.02, -0.17, 0.03), V_(-0.08, -0.3, -0.04)], [0.048 * f, 0.036 * f, 0.01])
        meta_part(f"Mon_Crab_Pincer{side}", pel, [shelld], res=0.007, faces=1500, parent=claw, loc=tuple(hinge))
        mb = CMB()
        for k in range(3):
            mb.add('sphere', M_TOOTH, loc=tuple(V_(0.33, -0.66 - k * 0.06, 0.155)), scale=(0.014, 0.014, 0.018))
        mb.build(f"Mon_Crab_Teeth{side}", COLL, parent=claw)


# ------------------------------------------------------------------ キリカブー
def build_stump(x):
    r = root("Mon_Stump", x)
    bark = mat("StumpBark", (0.38, 0.25, 0.15), 0.95)
    barkd = mat("StumpBarkDark", (0.2, 0.13, 0.08), 0.95)
    ring = mat("StumpRing", (0.86, 0.7, 0.47), 0.8)
    ringd = mat("StumpRingDark", (0.6, 0.43, 0.26), 0.85)
    leaf = mat("StumpLeaf", (0.32, 0.64, 0.22), 0.6)
    moss = mat("StumpMoss", (0.3, 0.45, 0.16), 0.95)
    el = [E_cap((0, 0, 0.3), (0, 0, 0.95), 0.38), E_ell((0, 0, 0.3), 0.46, 0.44, 0.3)]
    roots = []
    for k in range(5):
        a = k / 5 * math.tau + 0.3
        d = Vector((math.sin(a), -math.cos(a), 0))
        roots.append(d)
        el += [E_cap(d * 0.3 + Vector((0, 0, 0.25)), d * 0.62 + Vector((0, 0, 0.04)), 0.11), E_ball(d * 0.65 + Vector((0, 0, 0.04)), 0.08)]
    me = meta_mesh("Mon_Stump_Body", el, res=0.014)
    TOP = 1.08
    for v in me.vertices:
        if v.co.z > TOP:
            v.co.z = TOP
    me.update()
    me = decimate(me, 9000)
    me.materials.append(bark)
    me.materials.append(ring)
    for p in me.polygons:
        if p.normal.z > 0.92 and p.center.z > TOP - 0.02:
            p.material_index = 1
    body = mesh_to_obj(me, "Mon_Stump_Body")
    body.parent = r
    surf = Surface(me)
    mb = CMB()
    # 樹皮の筋（顔のまわりは低い位置だけ）
    rng = random.Random(21)
    for k in range(16):
        a = k / 16 * math.tau + rng.uniform(-0.1, 0.1)
        aa = (a + math.pi) % math.tau - math.pi
        ztop = 0.42 if abs(aa) < 0.65 else TOP - 0.03
        pts = []
        z = 0.3
        while z <= ztop:
            p, _ = surf.radial(Vector((0, 0, z)), a + math.sin(z * 9 + k) * 0.04, maxd=1.0)
            pts.append(p)
            z += 0.08
        if len(pts) >= 2:
            mb.tube(pts, [0.022] * len(pts), barkd, seg=6)
    # 年輪
    for rr in (0.08, 0.16, 0.24, 0.31):
        pts = [Vector((math.sin(i / 28 * math.tau) * rr * (1 + 0.04 * math.sin(i * 1.7)), -math.cos(i / 28 * math.tau) * rr, TOP + 0.002)) for i in range(29)]
        mb.tube(pts, [0.007] * len(pts), ringd, seg=4, flat=0.3)
    mb.add('sphere', ringd, loc=(0.02, 0.01, TOP), scale=(0.025, 0.025, 0.006))
    # 顔
    hollow = mat("StumpHollow", (0.05, 0.03, 0.02), 0.9)
    glow = mat("StumpEye", (1.0, 0.85, 0.3), 0.3, emit=(1.0, 0.8, 0.25), emit_strength=4.0)
    for s in (-1, 1):
        p, n = surf_point(surf, s * 0.14, 0.8)
        if p:
            e = basis_euler(n)
            mb.add('sphere', hollow, loc=p - n * 0.02, rot=e, scale=(0.075, 0.03, 0.09))
            mb.add('sphere', glow, loc=p + n * 0.004 + Vector((0, 0, -0.01)), rot=e, scale=(0.028, 0.02, 0.034))
        p1, n1 = surf_point(surf, s * 0.06, 0.93)
        p2, n2 = surf_point(surf, s * 0.22, 0.88)
        if p1 and p2:
            mb.tube([p1 + n1 * 0.015, p2 + n2 * 0.015], [0.032, 0.026], barkd, seg=8)
    p, n = surf_point(surf, 0, 0.55)
    if p:
        e = basis_euler(n)
        mb.add('sphere', hollow, loc=p - n * 0.02, rot=e, scale=(0.15, 0.03, 0.065))
        for s in (-1, 1):
            mb.add('cyl', ring, loc=p + Vector((s * 0.06, -0.012, 0.045)), rot=(math.pi, 0, 0), r1=0.022, r2=0.0, depth=0.05, seg=5)
    p, n = surf_point(surf, 0, 0.68)
    if p:
        mb.add('sphere', barkd, loc=p, rot=basis_euler(n), scale=(0.05, 0.04, 0.04))
    # 根元のコケ
    for d in roots[::2]:
        mb.add('ico', moss, loc=tuple(d * 0.5 + Vector((0, 0, 0.18))), r=0.12, sub=2, scale=(1.3, 1.3, 0.4), jitter=0.03)
    # 頭の新芽
    mb.tube([(0.1, 0.05, TOP), (0.11, 0.05, TOP + 0.12), (0.14, 0.04, TOP + 0.22)], [0.018, 0.014, 0.01], leaf, seg=6)
    for s in (-1, 1):
        mb.add('sphere', leaf, loc=(0.14 + s * 0.08, 0.04, TOP + 0.25), rot=(0, s * 0.5, 0), scale=(0.09, 0.035, 0.03))
    mb.build("Mon_Stump_Parts", COLL, parent=body)
    # 枝の腕
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.tube([(0, 0, 0), (sx * 0.22, -0.02, 0.08), (sx * 0.42, -0.05, 0.22), (sx * 0.55, -0.06, 0.4)], [0.07, 0.055, 0.04, 0.02], bark, seg=10)
        mb.tube([(sx * 0.42, -0.05, 0.22), (sx * 0.55, -0.08, 0.18), (sx * 0.63, -0.1, 0.24)], [0.025, 0.015, 0.008], bark, seg=6)
        mb.add('ico', leaf, loc=(sx * 0.56, -0.06, 0.46), r=0.13, sub=2, scale=(1, 0.85, 0.75), jitter=0.04, seed=3)
        mb.add('ico', leaf, loc=(sx * 0.64, -0.1, 0.28), r=0.08, sub=2, jitter=0.03, seed=4)
        for k in range(4):
            a = k * 1.6
            mb.add('sphere', leaf, loc=(sx * (0.56 + math.cos(a) * 0.12), -0.06 + math.sin(a) * 0.1, 0.5 + 0.05 * k % 0.1), rot=(a, 0.4, 0), scale=(0.08, 0.03, 0.025))
        mb.build(f"Mon_Stump_Arm{side}", COLL, loc=(sx * 0.36, 0, 0.72), parent=body)


# ------------------------------------------------------------------ ほねせんし
def build_skeleton(x):
    r = root("Mon_Skeleton", x)
    bone = mat("SkelBone", (0.9, 0.86, 0.74), 0.6)
    boned = mat("SkelBoneDark", (0.55, 0.5, 0.42), 0.8)
    iron = mat("RustIron", (0.42, 0.37, 0.33), 0.55, 0.7)
    rust = mat("Rust", (0.5, 0.26, 0.12), 0.9)
    blade = mat("RustBlade", (0.7, 0.68, 0.64), 0.42, 0.85)
    cloth = mat("SkelCloth", (0.38, 0.12, 0.1), 0.9, double=True)
    glow = mat("SkullGlow", (1.0, 0.25, 0.15), 0.2, emit=(1.0, 0.2, 0.1), emit_strength=6.0)
    hollow = mat("SkullHollow", (0.03, 0.02, 0.02), 0.9)
    mb = CMB()
    # 骨盤
    mb.add('sphere', bone, loc=(0, 0, 0.98), scale=(0.15, 0.09, 0.07))
    for s in (-1, 1):
        mb.add('sphere', bone, loc=(s * 0.12, 0.01, 1.04), rot=(0, s * 0.4, 0), scale=(0.09, 0.05, 0.08))
    # 背骨
    spine = []
    for i in range(10):
        z = 1.03 + i * 0.056
        y = 0.05 + 0.03 * math.sin(i / 9 * math.pi)
        spine.append(Vector((0, y, z)))
        mb.add('sphere', bone, loc=(0, y, z), scale=(0.034, 0.03, 0.02))
        mb.add('cube', boned, loc=(0, y + 0.035, z - 0.01), rot=(0.5, 0, 0), scale=(0.008, 0.025, 0.008))
    mb.tube(spine, [0.016] * len(spine), boned, seg=6)
    # 肋骨
    for i in range(6):
        z = 1.47 - i * 0.05
        rx = 0.12 + 0.05 * math.sin((i + 1) / 7 * math.pi)
        ry = 0.1 + 0.025 * math.sin((i + 1) / 7 * math.pi)
        for s in (-1, 1):
            pts = [Vector((s * rx * math.sin(th), -0.04 + ry * math.cos(th), z - 0.05 * math.sin(th))) for th in [0.25 + k * 0.33 for k in range(8)]]
            mb.tube(pts, [0.015] * 8, bone, seg=6)
    mb.tube([(0, -0.16, 1.48), (0, -0.17, 1.3)], [0.022, 0.018], bone, seg=8, flat=0.5)
    for s in (-1, 1):
        mb.tube([(0, -0.12, 1.53), (s * 0.12, -0.08, 1.56), (s * 0.2, -0.02, 1.54)], [0.017, 0.016, 0.018], bone, seg=6)
        mb.add('sphere', bone, loc=(s * 0.1, 0.1, 1.42), rot=(0, 0, s * 0.2), scale=(0.07, 0.015, 0.09))
    for i in range(3):
        mb.add('sphere', bone, loc=(0, 0.03, 1.6 + i * 0.03), scale=(0.025, 0.025, 0.014))
    # ベルトと腰布
    belt = [Vector((math.sin(i / 20 * math.tau) * 0.17, -math.cos(i / 20 * math.tau) * 0.11, 1.0)) for i in range(21)]
    mb.tube(belt, [0.02] * 21, iron, seg=6, flat=1.8)
    mb.add('cube', rust, loc=(0, -0.125, 1.0), scale=(0.07, 0.024, 0.06))
    for k, (ox, h) in enumerate(((-0.06, 0.2), (0.0, 0.26), (0.07, 0.18))):
        mb.poly([(ox - 0.045, -0.12, 0.99), (ox + 0.045, -0.12, 0.99), (ox + 0.03, -0.13 - h * 0.1, 0.99 - h), (ox - 0.02, -0.13 - h * 0.1, 0.99 - h + 0.03)],
                [(0, 1, 2, 3)], cloth)
    body = mb.build("Mon_Skeleton_Body", COLL, parent=r)

    # 頭蓋骨
    hel = [E_ell((0, 0.01, 0.11), 0.105, 0.125, 0.11), E_ell((0, -0.06, 0.04), 0.09, 0.08, 0.07),
           E_ell((0, -0.08, -0.03), 0.065, 0.06, 0.04), E_ell((0, -0.055, -0.085), 0.07, 0.07, 0.028)]
    for s in (-1, 1):
        hel.append(E_ell((s * 0.075, -0.06, 0.03), 0.035, 0.04, 0.03))
    head, hme = meta_part("Mon_Skeleton_Head", hel, [bone], res=0.006, faces=4000, parent=body, loc=(0, 0.0, 1.69))
    hs = Surface(hme)
    mb = CMB()
    for s in (-1, 1):
        p, n = hs.ray(Vector((s * 0.045, -1, 0.065)), Vector((0, 1, 0)))
        if p:
            e = basis_euler(n)
            mb.add('sphere', hollow, loc=p - n * 0.006, rot=e, scale=(0.036, 0.025, 0.032))
            mb.add('sphere', glow, loc=p + n * 0.002, rot=e, scale=(0.012, 0.01, 0.013))
    p, n = hs.ray(Vector((0, -1, 0.005)), Vector((0, 1, 0)))
    if p:
        mb.add('sphere', hollow, loc=p - n * 0.004, rot=basis_euler(n), scale=(0.014, 0.01, 0.022))
    for k in range(7):
        a = (k - 3) * 0.14
        mb.add('cube', M_TOOTH, loc=(math.sin(a) * 0.06, -0.11 + (1 - math.cos(a)) * 0.06, -0.058), scale=(0.015, 0.012, 0.022))
    # さびた兜と角
    mb.add('cyl', iron, loc=(0, 0.01, 0.15), r1=0.125, r2=0.112, depth=0.05, seg=24, scale=(1, 1.15, 1))
    mb.add('sphere', iron, loc=(0, 0.01, 0.17), scale=(0.118, 0.138, 0.085))
    for s in (-1, 1):
        mb.tube([(s * 0.11, 0.0, 0.18), (s * 0.18, -0.02, 0.25), (s * 0.2, -0.05, 0.34)], [0.025, 0.016, 0.003], bone, seg=8)
    mb.build("Mon_Skeleton_HeadParts", COLL, parent=head)

    # 腕（L＝盾、R＝剣）
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.add('sphere', bone, loc=(0, 0, 0), scale=(0.038, 0.038, 0.038))
        mb.tube([(0, 0, 0), (sx * 0.02, 0, -0.3)], [0.026, 0.021], bone, seg=8)
        mb.add('sphere', bone, loc=(sx * 0.02, 0, -0.3), scale=(0.032, 0.032, 0.032))
        for o in (-0.014, 0.014):
            mb.tube([(sx * 0.02 + o, 0, -0.3), (sx * 0.02 + o, -0.16, -0.52)], [0.013, 0.011], bone, seg=6)
        hand = Vector((sx * 0.02, -0.18, -0.56))
        mb.add('sphere', bone, loc=tuple(hand), scale=(0.035, 0.03, 0.04))
        for k in range(3):
            mb.tube([hand + Vector(((k - 1) * 0.015, -0.02, -0.02)), hand + Vector(((k - 1) * 0.017, -0.05, -0.05)), hand + Vector(((k - 1) * 0.017, -0.03, -0.08))],
                    [0.008, 0.007, 0.005], bone, seg=5)
        if side == "R":
            d = Vector((sx * 0.42, -0.5, 0.76)).normalized()
            rot = tuple(Vector((0, 0, 1)).rotation_difference(d).to_euler())
            g = hand + Vector((0, -0.02, -0.03))
            mb.add('cube', blade, loc=tuple(g + d * 0.45), rot=rot, scale=(0.06, 0.014, 0.72))
            cone_to(mb, blade, g + d * 0.81, d, 0.042, 0.1, seg=4)
            mb.add('cube', iron, loc=tuple(g + d * 0.075), rot=rot, scale=(0.17, 0.035, 0.028))
            mb.tube([g - d * 0.05, g + d * 0.06], [0.014, 0.014], mat("Grip", (0.25, 0.15, 0.08), 0.8), seg=6)
            mb.add('sphere', iron, loc=tuple(g - d * 0.07), scale=(0.022, 0.022, 0.022))
        else:
            c = hand + Vector((sx * 0.07, -0.02, 0.06))
            sh_rot = (0, sx * math.pi / 2, -sx * 0.6)
            mb.add('cyl', rust, loc=tuple(c), rot=sh_rot, r1=0.2, r2=0.2, depth=0.03, seg=28)
            mb.add('cyl', iron, loc=tuple(c), rot=sh_rot, r1=0.215, r2=0.205, depth=0.02, seg=28)
            q = Euler(sh_rot).to_matrix()
            ax = q @ Vector((0, 0, 1))
            mb.add('sphere', iron, loc=tuple(c + ax * 0.025), scale=(0.05, 0.05, 0.05))
            for k in range(8):
                a = k / 8 * math.tau
                off = q @ Vector((math.cos(a) * 0.16, math.sin(a) * 0.16, 0.018))
                mb.add('sphere', iron, loc=tuple(c + off), scale=(0.012, 0.012, 0.012))
        mb.build(f"Mon_Skeleton_Arm{side}", COLL, loc=(sx * 0.22, 0, 1.52), parent=body)

    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.add('sphere', bone, loc=(0, 0, 0), scale=(0.04, 0.04, 0.04))
        mb.tube([(0, 0, 0), (0, 0, -0.44)], [0.03, 0.025], bone, seg=8)
        mb.add('sphere', bone, loc=(0, -0.012, -0.45), scale=(0.038, 0.034, 0.036))
        for o in (-0.014, 0.014):
            mb.tube([(o, 0, -0.46), (o, 0.0, -0.86)], [0.016, 0.013], bone, seg=6)
        mb.add('sphere', bone, loc=(0, -0.05, -0.895), scale=(0.045, 0.1, 0.025))
        for k in range(3):
            mb.tube([((k - 1) * 0.022, -0.12, -0.9), ((k - 1) * 0.026, -0.18, -0.915)], [0.01, 0.007], bone, seg=5)
        mb.build(f"Mon_Skeleton_Leg{side}", COLL, loc=(sx * 0.1, 0, 0.94), parent=r)


# ------------------------------------------------------------------ おにび
def build_wisp(x):
    r = root("Mon_Wisp", x)
    core = mat("FlameCore", (1.0, 0.86, 0.45), 0.4, emit=(1.0, 0.75, 0.3), emit_strength=2.6)
    mid = mat("FlameMid", (1.0, 0.45, 0.1), 0.4, emit=(1.0, 0.36, 0.05), emit_strength=2.8)
    # 顔のある芯（下半分が見える）
    body, me = meta_part("Mon_Wisp_Body", [E_ell((0, 0, 0), 0.3, 0.28, 0.29)], [core], res=0.01, faces=4000, parent=r, loc=(0, 0, 1.35))
    surf = Surface(me)
    # 芯の上半分を包み込んで渦を巻きながら立ち上がる炎
    rng = random.Random(7)
    meta_part("Mon_Wisp_Flame", [E_ell((0, 0.03, 0.1), 0.31, 0.295, 0.21)], [mid], res=0.01, faces=3000, parent=body)
    mb = CMB()
    for k in range(10):
        a = k / 10 * math.tau + rng.uniform(-0.15, 0.15)
        rr = 0.21 if k else 0.0
        h = rng.uniform(0.28, 0.5) if k else 0.78
        pts = []
        for j in range(8):
            t = j / 7
            aa = a + 0.45 * t + 0.12 * math.sin(t * 5 + k)
            rad = rr * (1 + 0.1 * math.sin(t * math.pi) - 0.4 * t)
            pts.append(Vector((math.sin(aa) * rad, math.cos(aa) * rad * 0.85 + 0.04 + 0.05 * t, 0.12 + h * t)))
        w = 0.095 if k else 0.15
        mb.tube(pts, [w * (1 - t) ** 0.8 + 0.004 for t in [j / 7 for j in range(8)]], mid, seg=14)
    mb.build("Mon_Wisp_Tongues", COLL, parent=body)
    mb = CMB()
    for s in (-1, 1):
        p, n = surf_point(surf, s * 0.1, -0.04)
        if p:
            e = basis_euler(n)
            mb.add('sphere', M_PUPIL, loc=p - n * 0.005, rot=e, scale=(0.045, 0.02, 0.064))
            mb.add('sphere', M_EYEW, loc=p + n * 0.01 + Vector((0.012, 0, 0.024)), rot=e, scale=(0.014, 0.008, 0.016))
            mb.add('sphere', M_CHEEK, loc=p - n * 0.004 + Vector((s * 0.06, 0, -0.07)), rot=e, scale=(0.04, 0.01, 0.022))
    p, n = surf_point(surf, 0, -0.15)
    if p:
        mb.add('sphere', M_MOUTH, loc=p - n * 0.01, rot=basis_euler(n), scale=(0.07, 0.02, 0.035))
    mb.build("Mon_Wisp_Face", COLL, parent=body)
    mb = CMB()
    for k in range(9):
        a_ = k / 9 * math.tau
        rr = rng.uniform(0.42, 0.62)
        mb.add('ico', mid if k % 2 else core, loc=(math.cos(a_) * rr, math.sin(a_) * rr, rng.uniform(-0.25, 0.55)), r=rng.uniform(0.025, 0.045), sub=2)
    mb.build("Mon_Wisp_Embers", COLL, loc=(0, 0, 1.35), parent=r)


# ------------------------------------------------------------------ ドクコブラ
def build_snake(x):
    r = root("Mon_Snake", x)
    sc = mat("SnakeScale", (0.33, 0.56, 0.2), 0.45)
    scd = mat("SnakeScaleDark", (0.14, 0.28, 0.09), 0.5)
    belly = mat("SnakeBelly", (0.93, 0.85, 0.5), 0.55)
    N = 96
    pts, radii = [], []
    for i in range(N):
        t = i / (N - 1)
        a = t * 2.1 * math.tau
        R = 0.62 - 0.42 * t
        pts.append(Vector((math.cos(a) * R, math.sin(a) * R, 0.075 + 0.22 * t + 0.02 * smoothstep(0.0, 0.3, t))))
        radii.append(0.006 + 0.084 * smoothstep(0.0, 0.45, t))
    mb = CMB()
    mb.tube(pts, radii, sc, seg=22)
    body = mb.build("Mon_Snake_Body", COLL, parent=r)
    me = body.data
    me.materials.append(scd)
    me.materials.append(belly)
    for p in me.polygons:
        if p.normal.z < -0.25:
            p.material_index = 2
    pts = pts[::3]
    radii = radii[::3]
    N = len(pts)
    ssurf = Surface(me)
    mb = CMB()
    for i in range(2, N - 1):
        tng = (pts[i + 1] - pts[i - 1]).normalized()
        for off in (0.0, 0.5):
            c = pts[i].lerp(pts[i + 1], off)
            hp, hn = ssurf.ray(c + Vector((0, 0, 0.4)), Vector((0, 0, -1)))
            if hp is None:
                continue
            rr = radii[i] * (0.5 if off == 0 else 0.3)
            e = basis_euler(hn, up=tng)
            mb.add('sphere', scd, loc=hp - hn * 0.006, rot=e, scale=(rr, 0.008, rr * 1.3))
    mb.build("Mon_Snake_Spots", COLL, parent=body)
    # 首（とぐろの中心がピボット）とフード
    npts = [Vector(v) for v in ((0, 0, 0), (0, 0.06, 0.22), (0, 0.02, 0.45), (0, -0.08, 0.62), (0, -0.14, 0.72))]
    nel = E_chain(npts, [0.13, 0.12, 0.1, 0.09, 0.085]) + [E_ell((0, -0.03, 0.52), 0.2, 0.035, 0.2)]

    def a_neck(c, n):
        if n.y < -0.45:
            return 2
        return 0
    neck, _ = meta_part("Mon_Snake_Neck", nel, [sc, scd, belly], res=0.009, faces=4000, assign=a_neck, parent=r, loc=tuple(pts[-1]))
    mb = CMB()
    for s in (-1, 1):
        mb.add('sphere', scd, loc=(s * 0.09, 0.01, 0.55), rot=(0, 0, 0), scale=(0.055, 0.03, 0.065))
        mb.add('sphere', belly, loc=(s * 0.09, 0.025, 0.555), scale=(0.025, 0.02, 0.03))
    mb.build("Mon_Snake_NeckParts", COLL, parent=neck)
    hel = [E_ell((0, -0.08, 0.02), 0.1, 0.15, 0.065), E_ell((0, 0.02, 0.03), 0.085, 0.08, 0.07), E_ell((0, -0.2, 0.0), 0.06, 0.05, 0.04)]
    head, hme = meta_part("Mon_Snake_Head", hel, [sc, scd, belly], res=0.006, faces=3500,
                          assign=lambda c, n: 2 if n.z < -0.4 else (1 if n.z > 0.7 and c.y > -0.12 else 0), parent=neck, loc=(0, -0.14, 0.75))
    hs = Surface(hme)
    mb = CMB()
    iris = mat("SnakeIris", (1.0, 0.8, 0.1), 0.15)
    for s in (-1, 1):
        p, n = hs.ray(Vector((s * 1.0, -0.08, 0.045)), Vector((-s, 0, 0)))
        if p:
            e = basis_euler((n + Vector((0, -0.6, 0.2))).normalized())
            mb.add('sphere', iris, loc=p - n * 0.008, rot=e, scale=(0.032, 0.02, 0.026))
            mb.add('sphere', M_PUPIL, loc=p + n * 0.006, rot=e, scale=(0.007, 0.012, 0.022))
            mb.add('cube', scd, loc=p + n * 0.01 + Vector((0, 0, 0.025)), rot=(0, s * 0.3, 0), scale=(0.035, 0.012, 0.01))
        mb.add('sphere', M_PUPIL, loc=(s * 0.022, -0.245, 0.02), scale=(0.008, 0.006, 0.006))
        mb.add('cyl', M_TOOTH, loc=(s * 0.03, -0.2, -0.045), rot=(math.pi, 0, 0), r1=0.009, r2=0.0, depth=0.04, seg=5)
        mb.add('cube', M_TONGUE, loc=(s * 0.014, -0.385, -0.012), rot=(0, 0, s * 0.4), scale=(0.009, 0.055, 0.006))
    mb.add('cube', M_TONGUE, loc=(0, -0.3, -0.012), scale=(0.013, 0.13, 0.008))
    mb.add('sphere', M_MOUTH, loc=(0, -0.13, -0.03), scale=(0.07, 0.11, 0.008))
    mb.build("Mon_Snake_HeadParts", COLL, parent=head)


# ------------------------------------------------------------------ ガーゴイル
def build_gargoyle(x):
    r = root("Mon_Gargoyle", x)
    st = mat("GargStone", (0.47, 0.48, 0.53), 0.88)
    std = mat("GargStoneDark", (0.27, 0.27, 0.32), 0.9)
    eyeg = mat("GargEye", (0.6, 1.0, 0.4), 0.2, emit=(0.5, 1.0, 0.3), emit_strength=6.0)
    memb = mat("GargWing", (0.3, 0.27, 0.34), 0.8, double=True)
    el = [
        E_ell((0, 0.0, 0.12), 0.27, 0.2, 0.22),
        E_ell((0, 0.0, -0.1), 0.16, 0.14, 0.15),
        E_ell((0, 0.02, -0.26), 0.18, 0.15, 0.1),
        E_ell((0, -0.1, 0.47), 0.15, 0.15, 0.14),
        E_ell((0, -0.25, 0.42), 0.085, 0.11, 0.065),
        E_ell((0, -0.21, 0.35), 0.08, 0.09, 0.04),
        E_ell((0, -0.19, 0.52), 0.13, 0.05, 0.035),
        E_cap((0, -0.02, 0.26), (0, -0.07, 0.38), 0.1),
    ]
    for s in (-1, 1):
        el += [E_ell((s * 0.12, -0.12, 0.15), 0.12, 0.07, 0.1),
               E_ball((s * 0.3, 0, 0.22), 0.11),
               E_cap((s * 0.31, 0, 0.2), (s * 0.38, 0.02, -0.05), 0.068),
               E_cap((s * 0.38, 0.02, -0.05), (s * 0.33, -0.2, -0.2), 0.056),
               E_ell((s * 0.32, -0.25, -0.26), 0.055, 0.06, 0.07),
               E_cap((s * 0.12, 0, -0.3), (s * 0.18, -0.2, -0.42), 0.085),
               E_cap((s * 0.18, -0.2, -0.42), (s * 0.17, 0.04, -0.6), 0.055),
               E_cap((s * 0.17, 0.04, -0.6), (s * 0.17, -0.08, -0.7), 0.042),
               E_dir((s * 0.14, -0.06, 0.53), (s, 0.5, 0.5), 0.14, 0.05, 0.02)]
    tpts = [Vector(v) for v in ((0, 0.15, -0.28), (0, 0.38, -0.4), (0, 0.52, -0.62), (0.06, 0.56, -0.84))]
    el += E_chain(tpts, [0.055, 0.04, 0.028, 0.012])
    body, me = meta_part("Mon_Gargoyle_Body", el, [st, std], res=0.01, faces=12000, assign=lambda c, n: 1 if c.z < -0.62 else 0, parent=r, loc=(0, 0, 1.45))
    surf = Surface(me)
    mb = CMB()
    for s in (-1, 1):
        p, n = surf.ray(Vector((s * 0.07, -2, 0.47)), Vector((0, 1, 0)))
        if p:
            e = basis_euler(n)
            mb.add('sphere', M_PUPIL, loc=p - n * 0.008, rot=e, scale=(0.042, 0.015, 0.03))
            mb.add('sphere', eyeg, loc=p - n * 0.002, rot=e, scale=(0.032, 0.014, 0.018))
        mb.tube([(s * 0.08, -0.1, 0.57), (s * 0.17, -0.02, 0.72), (s * 0.17, 0.13, 0.83), (s * 0.1, 0.24, 0.81)], [0.042, 0.03, 0.016, 0.003], std, seg=10)
        for k in (-1, 0, 1):
            cone_to(mb, std, (s * 0.32 + k * 0.025, -0.28, -0.31), (k * 0.2, -0.5, -1), 0.013, 0.07)
            cone_to(mb, std, (s * 0.17 + k * 0.03, -0.16, -0.71), (k * 0.2, -1, -0.3), 0.012, 0.06)
    p, n = surf.ray(Vector((0, -2, 0.375)), Vector((0, 1, 0)))
    if p:
        mb.add('sphere', M_MOUTH, loc=p - n * 0.01, rot=basis_euler(n), scale=(0.07, 0.02, 0.022))
        for s in (-1, 1):
            mb.add('cyl', M_TOOTH, loc=p + Vector((s * 0.04, -0.008, -0.004)), rot=(math.pi, 0, 0), r1=0.012, r2=0.0, depth=0.05, seg=5)
            mb.add('cyl', M_TOOTH, loc=p + Vector((s * 0.025, -0.01, -0.028)), rot=(0, 0, 0), r1=0.01, r2=0.0, depth=0.035, seg=5)
    for i in range(5):
        cone_to(mb, std, (0, 0.15 + i * 0.01, 0.34 - i * 0.12), (0, 1, 0.3), 0.025, 0.09)
    mb.build("Mon_Gargoyle_Parts", COLL, parent=body)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        arm = [Vector((0, 0, 0.05)), Vector((0.35 * sx, 0.12, 0.27)), Vector((0.6 * sx, 0.18, 0.4))]
        mb.tube(arm, [0.045, 0.038, 0.03], st, seg=8)
        hand = arm[-1]
        fingers = [Vector((1.05 * sx, 0.2, 0.47)), Vector((1.15 * sx, 0.2, 0.1)), Vector((0.95 * sx, 0.2, -0.2)), Vector((0.6 * sx, 0.15, -0.3))]
        for f in fingers:
            mb.tube([hand, hand.lerp(f, 0.5) + Vector((0, 0, 0.03)), f], [0.024, 0.016, 0.006], st, seg=6)
        cone_to(mb, std, hand, (0.3 * sx, 0, 1), 0.025, 0.12)
        outline = [Vector((0, 0.02, 0.06)), arm[1], hand, fingers[0]]
        prev = fingers[0]
        for f in fingers[1:]:
            outline += [prev.lerp(f, 0.5).lerp(hand, 0.25), f]
            prev = f
        outline += [Vector((0.2 * sx, 0.08, -0.2)), Vector((0, 0.02, -0.12))]
        cen = Vector((0.45 * sx, 0.1, 0.1))
        verts = [tuple(cen)] + [tuple(v) for v in outline]
        mb.poly(verts, [(0, i, i + 1) for i in range(1, len(verts) - 1)], memb, smooth=True)
        mb.build(f"Mon_Gargoyle_Wing{side}", COLL, loc=(sx * 0.16, 0.12, 1.62), parent=r)



# ------------------------------------------------------------------ 棺桶（たおれた仲間）
def build_coffin(x):
    r = root("Mon_Coffin", x)
    wood = mat("CoffinWood", (0.32, 0.18, 0.1), 0.6)
    lid = mat("CoffinLid", (0.46, 0.27, 0.15), 0.55)
    grain = mat("CoffinGrain", (0.26, 0.14, 0.08), 0.7)
    iron = mat("CoffinIron", (0.2, 0.2, 0.22), 0.4, 0.8)
    gold = mat("CoffinGold", (1.0, 0.78, 0.32), 0.3, 1.0)
    P = [(-0.19, 0.0), (0.19, 0.0), (0.31, 1.18), (0.21, 1.72), (-0.21, 1.72), (-0.31, 1.18)]
    D = 0.19

    def prism(mb, pts, y0, y1, m, z0=0.0):
        n = len(pts)
        verts = [(px, y0, pz + z0) for px, pz in pts] + [(px, y1, pz + z0) for px, pz in pts]
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, n + i, n + j, j))
        mb.poly(verts, faces, m)

    mb = CMB()
    prism(mb, P, -D, D, wood)
    bmesh.ops.recalc_face_normals(mb.bm, faces=mb.bm.faces[:])
    body = mb.build("Mon_Coffin_Body", COLL, parent=r)

    # ふたの板・縁取り・十字架・びょう（前後両面）
    mb = CMB()
    cx = sum(p[0] for p in P) / len(P)
    cz = sum(p[1] for p in P) / len(P)
    inset = [(cx + (px - cx) * 0.84, cz + (pz - cz) * 0.9) for px, pz in P]
    for sgn in (-1, 1):
        y_out = sgn * (D + 0.022)
        prism(mb, inset, sgn * D, y_out, lid)
        # 木目
        for k in range(-3, 4):
            xx = k * 0.055
            mb.add('cube', grain, loc=(xx, y_out + sgn * 0.001, 0.86), scale=(0.006, 0.002, 1.35 - abs(k) * 0.08))
        # 縁取り
        ring = [Vector((px, sgn * (D + 0.004), pz)) for px, pz in P]
        ring.append(ring[0])
        mb.tube(ring, [0.022] * len(ring), iron, seg=6)
        for px, pz in P:
            mb.add('sphere', gold, loc=(px * 0.93, sgn * (D + 0.02), pz + (0.05 if pz < 0.1 else -0.05 if pz > 1.6 else 0)), scale=(0.022, 0.012, 0.022))
        # 十字架
        yc = y_out + sgn * 0.012
        mb.add('cube', gold, loc=(0, yc, 1.08), scale=(0.07, 0.022, 0.78))
        mb.add('cube', gold, loc=(0, yc, 1.3), scale=(0.38, 0.022, 0.07))
    # 側面の金具（持ち手）
    for s in (-1, 1):
        for zz in (0.55, 1.0):
            ex = 0.19 + (0.31 - 0.19) * (zz / 1.18)
            mb.tube([(s * ex, -0.09, zz), (s * (ex + 0.05), -0.06, zz - 0.03), (s * (ex + 0.05), 0.06, zz - 0.03), (s * ex, 0.09, zz)], [0.012] * 4, iron, seg=6)
    bmesh.ops.recalc_face_normals(mb.bm, faces=mb.bm.faces[:])
    mb.build("Mon_Coffin_Trim", COLL, parent=body)

build_purun(0.0)
build_bat(2.5)
build_mushroom(5.0)
build_ghost(7.5)
build_golem(10.5)
build_dragon(16.0)
build_wolf(20.0)
build_crab(23.0)
build_stump(26.0)
build_skeleton(29.0)
build_wisp(32.0)
build_snake(35.0)
build_gargoyle(38.0)
build_coffin(41.0)
exec(compile(open(os.path.join(_here, "monsters_sequel.py"), encoding="utf-8").read(), "monsters_sequel.py", "exec"))

if _temp_link:
    SCENE.collection.children.unlink(COLL)
print("monsters done")
