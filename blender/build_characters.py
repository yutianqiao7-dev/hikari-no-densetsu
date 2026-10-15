# -*- coding: utf-8 -*-
"""
ひかりの伝説 — 人型キャラクター生成（build_world.py の後に実行）

  1. メタボールで体全体を 1 枚の連続した面として造形（関節のつなぎ目が自然に溶け合う）
  2. 部位ごとにマテリアルを塗り分け、髪・顔・服・装備を追加
  3. 共通のアーマチュアを作り、距離ベースの滑らかなウェイトでスキニング
  4. Hero のアーマチュアにアクション（Idle / Walk / Run / Attack / Cast / Hurt / Victory / Down）を作成
     → ゲーム側では骨の名前が同じなので全員で共有できる

座標: Blender (x, y, z)、キャラクターは -Y を向く。足元 z=0、身長 約 1.75m。
"""
import os, sys, math, random
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\OWNER-1121R\Desktop\クロード\ドラクエ\blender"
sys.path.insert(0, _here)
import importlib, bkit
importlib.reload(bkit)
from bkit import *
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion, Euler
from mathutils.bvhtree import BVHTree
import bmeta
importlib.reload(bmeta)
from bmeta import CMB, E_ball, E_cap, E_ell, E_dir, meta_mesh, decimate, mesh_to_obj, Surface, basis_euler

COLL = bpy.data.collections["Characters"]
bmeta.set_collection(COLL)
SCENE = bpy.context.scene
_temp_link = COLL.name not in SCENE.collection.children
if _temp_link:
    SCENE.collection.children.link(COLL)

for sc in bpy.data.scenes:
    sc.render.fps = 30

# ------------------------------------------------------------------ 骨格
HEAD_PIVOT = Vector((0, 0, 1.50))


def bone_table():
    t = [
        ('hips', (0, 0, 0.93), (0, 0, 1.05), None, 0.14),
        ('spine', (0, 0, 1.05), (0, 0, 1.22), 'hips', 0.13),
        ('chest', (0, 0, 1.22), (0, 0, 1.41), 'spine', 0.15),
        ('neck', (0, 0, 1.41), (0, -0.005, 1.51), 'chest', 0.05),
        ('head', (0, -0.005, 1.51), (0, -0.005, 1.78), 'neck', 0.11),
    ]
    for side, s in (('L', 1), ('R', -1)):
        t += [
            (f'shoulder.{side}', (s * 0.03, 0, 1.385), (s * 0.165, 0.01, 1.385), 'chest', 0.06),
            (f'upper_arm.{side}', (s * 0.165, 0.01, 1.385), (s * 0.30, 0.015, 1.133), f'shoulder.{side}', 0.048),
            (f'forearm.{side}', (s * 0.30, 0.015, 1.133), (s * 0.415, -0.01, 0.917), f'upper_arm.{side}', 0.04),
            (f'hand.{side}', (s * 0.415, -0.01, 0.917), (s * 0.445, -0.025, 0.838), f'forearm.{side}', 0.035),
            (f'thigh.{side}', (s * 0.092, 0, 0.92), (s * 0.10, -0.005, 0.50), 'hips', 0.08),
            (f'shin.{side}', (s * 0.10, -0.005, 0.50), (s * 0.10, 0.015, 0.085), f'thigh.{side}', 0.06),
            (f'foot.{side}', (s * 0.10, 0.015, 0.085), (s * 0.10, -0.115, 0.025), f'shin.{side}', 0.045),
        ]
    t += [
        ('cape.1', (0, 0.12, 1.38), (0, 0.16, 0.98), 'chest', 0.1),
        ('cape.2', (0, 0.16, 0.98), (0, 0.21, 0.52), 'cape.1', 0.1),
    ]
    return t


BONES = bone_table()
BMAP = {b[0]: b for b in BONES}
BODY_BONES = [b for b in BONES if not b[0].startswith('cape')]


def V(*a):
    return Vector(a if len(a) == 3 else a[0])


def seg_closest(p, a, b):
    a, b = Vector(a), Vector(b)
    d = b - a
    t = max(0.0, min(1.0, (p - a).dot(d) / d.length_squared))
    return (a + d * t - p).length, t


# ------------------------------------------------------------------ メタボール
def head_xf(el, hs):
    """頭部の要素を首の付け根を中心にスケール"""
    def P(p):
        return HEAD_PIVOT + (Vector(p) - HEAD_PIVOT) * hs
    k = el[0]
    if k == 'b':
        return ('b', P(el[1]), el[2] * hs)
    if k == 'c':
        return ('c', P(el[1]), P(el[2]), el[3] * hs)
    return ('e', P(el[1]), tuple(r * hs for r in el[2]), el[3])


# ------------------------------------------------------------------ 体の要素
def body_elems(cfg):
    b = cfg.get('build', 'male')
    hs = cfg.get('head_scale', 0.98)
    fem = b == 'female'
    lw = 0.86 if fem else (1.0 if b != 'slim' else 0.9)     # 手足の太さ
    sw = 0.88 if fem else 1.0                                  # 肩幅
    el = []
    # 胴体
    el += [
        E_ell((0, 0.006, 0.95), 0.150 if fem else 0.142, 0.10, 0.092),
        E_ell((0, 0.0, 1.09), 0.112 if fem else 0.122, 0.082, 0.11),
        E_ell((0, 0.006, 1.27), 0.148 * sw, 0.094, 0.118),
        E_cap((-0.08 * sw, 0.012, 1.395), (0.08 * sw, 0.012, 1.395), 0.04),
    ]
    if fem:
        for s in (-1, 1):
            el.append(E_ell((s * 0.05, -0.05, 1.27), 0.05, 0.045, 0.045))
    else:
        # 胸板：平たく横に広い（胸のふくらみに見えないように）
        el.append(E_ell((0, -0.026, 1.295), 0.135, 0.05, 0.062))
        for s in (-1, 1):
            el.append(E_ell((s * 0.058, -0.04, 1.30), 0.06, 0.03, 0.042))
    if b == 'portly':
        el.append(E_ell((0, -0.035, 1.08), 0.17, 0.15, 0.16))
    for s in (-1, 1):
        el.append(E_ell((s * 0.148 * sw, 0.008, 1.37), 0.062, 0.058, 0.055))
    el.append(E_cap((0, 0.008, 1.37), (0, -0.003, 1.52), 0.041 if not fem else 0.036))
    # 頭
    head = [
        E_ell((0, 0.010, 1.625), 0.094, 0.104, 0.108),
        E_ell((0, -0.024, 1.566), 0.056, 0.064, 0.056),
        E_ell((0, -0.064, 1.529), 0.027, 0.024, 0.021),
        E_ell((0, -0.097, 1.581), 0.0095, 0.012, 0.0145),
        E_cap((0, -0.088, 1.612), (0, -0.097, 1.586), 0.0055),
    ]
    for s in (-1, 1):
        head.append(E_ell((s * 0.041, -0.058, 1.576), 0.021, 0.017, 0.02))
        head.append(E_ell((s * 0.092, 0.006, 1.595), 0.011, 0.021, 0.03))
    el += [head_xf(e, hs) for e in head]
    # 腕
    for s in (-1, 1):
        sd = 'L' if s > 0 else 'R'
        sh, elb = Vector(BMAP[f'upper_arm.{sd}'][1]), Vector(BMAP[f'upper_arm.{sd}'][2])
        wr = Vector(BMAP[f'forearm.{sd}'][2])
        hd = (Vector(BMAP[f'hand.{sd}'][2]) - wr).normalized()
        el += [
            E_cap(sh, elb, 0.040 * lw),
            E_ell(sh.lerp(elb, 0.18), 0.056 * lw, 0.054 * lw, 0.056 * lw),
            E_dir(sh.lerp(elb, 0.55), elb - sh, 0.075, 0.043 * lw, 0.043 * lw),
            E_cap(elb, wr, 0.031 * lw),
            E_dir(elb.lerp(wr, 0.3), wr - elb, 0.07, 0.04 * lw, 0.037 * lw),
            E_ball(elb, 0.036 * lw),
            # 手首（手は build_hands で指まで作る）
            E_dir(wr + hd * 0.012, hd, 0.026, 0.027 * lw, 0.017),
        ]
    # 脚
    for s in (-1, 1):
        sd = 'L' if s > 0 else 'R'
        hp, kn = Vector(BMAP[f'thigh.{sd}'][1]), Vector(BMAP[f'thigh.{sd}'][2])
        an = Vector(BMAP[f'shin.{sd}'][2])
        el += [
            E_cap(hp, kn, 0.064 * lw),
            E_dir(hp.lerp(kn, 0.32) + Vector((0, -0.006, 0)), kn - hp, 0.14, 0.082 * lw, 0.08 * lw),
            E_ball(kn, 0.05 * lw),
            E_cap(kn, an, 0.042 * lw),
            E_dir(kn.lerp(an, 0.3) + Vector((0, 0.016, 0)), an - kn, 0.11, 0.055 * lw, 0.052 * lw),
            # ブーツ
            E_cap(an + Vector((0, -0.005, -0.01)), an + Vector((0, -0.01, 0.24)), 0.052 if cfg.get('boots', True) else 0.04),
            E_ell((s * 0.10, -0.04, 0.042), 0.046, 0.108, 0.042),
            E_ball((s * 0.10, 0.03, 0.045), 0.045),
        ]
    # 服のふくらみ
    return el


# ------------------------------------------------------------------ 部位判定・ウェイト
def side_ok(bn, x):
    if bn.endswith('.L') and x < -0.035:
        return False
    if bn.endswith('.R') and x > 0.035:
        return False
    return True


def nearest_bone(p):
    best = None
    for (bn, h, t, par, r) in BODY_BONES:
        if not side_ok(bn, p.x):
            continue
        d, tt = seg_closest(p, h, t)
        sc = d - r * 0.5
        if best is None or sc < best[0]:
            best = (sc, bn, tt)
    return best[1], best[2]


def weights_for(p, cfg, region=None):
    head_zone = p.z > 1.47 and abs(p.x) < 0.14
    cand = []
    for (bn, h, t, par, r) in BODY_BONES:
        if not side_ok(bn, p.x):
            continue
        if head_zone and bn not in ('head', 'neck'):
            continue
        d, _ = seg_closest(p, h, t)
        d = max(d - r * 0.55, 0.004)
        cand.append((1.0 / d ** 4, bn))
    cand.sort(reverse=True)
    cand = cand[:3]
    tot = sum(w for w, _ in cand)
    ws = {bn: w / tot for w, bn in cand if w / tot > 0.02}
    if region in ('robe', 'dress'):
        legs = {k: v for k, v in ws.items() if k.split('.')[0] in ('thigh', 'shin', 'foot')}
        lt = sum(legs.values()) or 1.0
        k_leg = 0.35 if region == 'robe' else 0.55
        ws = {'hips': 1.0 - k_leg}
        for k, v in legs.items():
            ws[k] = ws.get(k, 0) + k_leg * v / lt
        if not legs:
            ws = {'hips': 1.0}
    s = sum(ws.values())
    return {k: v / s for k, v in ws.items()}


def paint(cfg, bn, t, p):
    b = bn.split('.')[0]
    x, y, z = p
    tl = cfg.get('tunic_len', 0.86)
    if b == 'head':
        return 'skin'
    if b in ('neck', 'chest', 'shoulder') and abs(x) < 0.1 and z > 1.36:
        return 'top' if z < 1.425 else 'skin'
    if b in ('chest', 'spine', 'shoulder'):
        return 'top'
    if b == 'hips':
        if 0.935 < z < 0.99:
            return 'belt'
        return 'top' if z > tl else 'pants'
    if b in ('upper_arm', 'forearm') and 'under' in cfg['colors']:
        if b == 'forearm' and cfg.get('gloves') and t > 0.42:
            return 'glove'
        return 'under'
    if cfg.get('stockings') and b in ('thigh', 'shin') and cfg.get('boot_h', 0.33) <= z < 0.6:
        return 'stock' if int(z / 0.045) % 2 == 0 else 'stock2'
    if b == 'upper_arm':
        sl = cfg.get('sleeves', 'long')
        if sl == 'long':
            return 'top'
        return 'top' if t < (0.6 if sl == 'short' else 0.12) else 'skin'
    if b == 'forearm':
        if cfg.get('gloves') and t > 0.42:
            return 'glove'
        if cfg.get('sleeves', 'long') == 'long':
            return 'top' if t < 0.9 else 'skin'
        return 'skin'
    if b == 'hand':
        return 'glove' if cfg.get('gloves') else 'skin'
    if b == 'thigh':
        return 'top' if z > tl else 'pants'
    if b == 'shin':
        return 'boot' if z < cfg.get('boot_h', 0.33) else 'pants'
    if b == 'foot':
        return 'boot'
    return 'top'


def boundary_planes(cfg):
    """服の境目（袖口・裾・ベルト・ブーツ）をまっすぐにするための切断平面"""
    P = []
    up = Vector((0, 0, 1))
    torso = lambda c: abs(c.x) < 0.27 and c.z < 1.5
    if not cfg.get('robe'):
        P += [(Vector((0, 0, 0.935)), up, torso), (Vector((0, 0, 0.99)), up, torso)]
        tl = cfg.get('tunic_len', 0.86)
        P.append((Vector((0, 0, tl)), up, lambda c: abs(c.x) < 0.27 and 0.6 < c.z < 1.0))
    else:
        P.append((Vector((0, 0, 0.975)), up, lambda c: abs(c.x) < 0.36 and 0.6 < c.z < 1.2))
    if cfg.get('dress'):
        P += [(Vector((0, 0, 0.985)), up, lambda c: abs(c.x) < 0.36 and 0.6 < c.z < 1.2),
              (Vector((0, 0, 0.50)), up, lambda c: abs(c.x) < 0.36 and 0.3 < c.z < 0.7)]
    P.append((Vector((0, 0, 1.425)), up, lambda c: abs(c.x) < 0.1 and 1.3 < c.z < 1.55))
    if cfg.get('stockings'):
        for k in range(int(0.33 / 0.045), int(0.6 / 0.045) + 1):
            P.append((Vector((0, 0, k * 0.045)), up, lambda c: 0.02 < abs(c.x) < 0.24 and 0.25 < c.z < 0.65))
    sl = cfg.get('sleeves', 'long')
    for sd, sx in (('L', 1), ('R', -1)):
        ua, fa = BMAP[f'upper_arm.{sd}'], BMAP[f'forearm.{sd}']

        def near(seg):
            return lambda c, seg=seg: seg_closest(c, seg[1], seg[2])[0] < 0.085 and c.x * sx > 0.1
        if 'under' in cfg['colors']:
            a, b = Vector(ua[1]), Vector(ua[2])
            P.append((a.lerp(b, 0.06), (b - a).normalized(), near(ua)))
        elif sl != 'long':
            t = 0.6 if sl == 'short' else 0.12
            a, b = Vector(ua[1]), Vector(ua[2])
            P.append((a.lerp(b, t), (b - a).normalized(), near(ua)))
        ft = 0.42 if cfg.get('gloves') else (0.9 if sl == 'long' else None)
        if ft:
            a, b = Vector(fa[1]), Vector(fa[2])
            P.append((a.lerp(b, ft), (b - a).normalized(), near(fa)))
        bh = cfg.get('boot_h', 0.33)
        P.append((Vector((0, 0, bh)), up, lambda c, sx=sx: 0.02 < c.x * sx < 0.24 and c.z < 0.7))
    return P


def cut_body(me, cfg):
    bm = bmesh.new()
    bm.from_mesh(me)
    for (co, no, filt) in boundary_planes(cfg):
        faces = [f for f in bm.faces if filt(f.calc_center_median())]
        if not faces:
            continue
        edges = {e for f in faces for e in f.edges}
        verts = {v for f in faces for v in f.verts}
        bmesh.ops.bisect_plane(bm, geom=list(verts) + list(edges) + faces, dist=0.0004, plane_co=co, plane_no=no)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(me)
    bm.free()


def cmat(cfg, key):
    name = cfg['name']
    defaults = {'belt': (0.30, 0.19, 0.10), 'pants': cfg['colors'].get('robe', (0.3, 0.3, 0.3)), 'glove': (0.4, 0.27, 0.15),
                'boot': (0.32, 0.2, 0.1), 'stock2': (0.97, 0.95, 0.92)}
    col = cfg['colors'].get(key, defaults.get(key, (0.5, 0.5, 0.5)))
    rough = {'skin': 0.55, 'glove': 0.6, 'boot': 0.55, 'belt': 0.6, 'hair': 0.45, 'metal': 0.3}.get(key, 0.85)
    metal = 1.0 if key in ('metal', 'gold') else 0.0
    return mat(f"{name}_{key}", col, rough, metal)


def assign_vgroups(ob, wfun):
    me = ob.data
    groups = {}
    for v in me.vertices:
        for bn, w in wfun(v).items():
            if bn not in groups:
                groups[bn] = ob.vertex_groups.new(name=bn)
            groups[bn].add([v.index], w, 'REPLACE')


def rig_rigid(ob, bone):
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')


# ------------------------------------------------------------------ 表面スナップ
# ------------------------------------------------------------------ 顔
def build_face(cfg, surf):
    """描いた目（face.py）＋まつ毛の線・二重・眉・口・ほお紅"""
    import face
    importlib.reload(face)
    hs = cfg.get('head_scale', 0.98)
    fem = cfg.get('build') == 'female'
    name = cfg['name']

    def P(x, z):
        q = HEAD_PIVOT + (Vector((x, 0, z)) - HEAD_PIVOT) * hs
        return q.x, q.z

    def on(x, z, lift):
        px, pz = P(x, z)
        q, nn = surf.front(px, pz)
        return q + nn * lift

    hair_c = cfg['colors'].get('hair', (0.3, 0.3, 0.3))
    skin_c = cfg['colors'].get('skin', SKIN_C)
    lash = mat(name + "_Lash", tuple(c * 0.25 for c in hair_c) if sum(hair_c) < 1.6 else (0.12, 0.09, 0.08), 0.6)
    crease_m = mat(name + "_Crease", tuple(c * 0.72 for c in skin_c), 0.7)
    brow = mat(name + "_Brow", tuple(c * 0.7 for c in hair_c), 0.7)
    mouth = mat(name + "_Mouth", (0.62, 0.3, 0.28), 0.5)
    st_ = cfg.get('eye_style') or ('fem' if fem else 'male')
    eye_img = face.eye_image(name + "_EyeImg", cfg.get('eye', (0.25, 0.15, 0.08)), st_)
    eye_m = face.tex_mat(name + "_EyeTex", eye_img, 0.12)
    objs = []
    st = cfg.get('eye_style') or ('fem' if fem else 'male')
    W, Hh = {'cute': (0.047, 0.046), 'cool': (0.042, 0.03), 'fem': (0.042, 0.039)}.get(st, (0.039, 0.033))
    if cfg.get('eyes') == 'adult':        # 大人の男性は少し細い目
        W *= 0.95
        Hh *= 0.74
    cz = 1.596
    mb = CMB()
    for s_ in (-1, 1):
        cx = s_ * 0.040
        objs.append(face.surface_patch(surf, P, cx, cz, W, Hh, s_, eye_m, f"{name}_Eye{'L' if s_ > 0 else 'R'}", COLL, lift=0.0014))
        # 上まつ毛の線（目じりへ太く、はね上がる）
        pts, rad = [], []
        for k in range(11):
            a = 0.06 + k / 10 * 0.94
            x = cx + s_ * (a - 0.5) * W
            z = cz + (face.lid_top(a, st) - 0.5) * Hh + 0.0012
            pts.append(on(x, z, 0.0024))
            rad.append((0.0007 + 0.0026 * math.sin(math.pi * (0.12 + a * 0.82)) ** 0.6 * (0.6 + 0.4 * a)) * (1.25 if st in ('cool', 'cute') else 1.0))
        for ext, up in ((0.07, 0.04), (0.13, 0.1)):
            a = 1 + ext
            pts.append(on(cx + s_ * (a - 0.5) * W, cz + (face.lid_top(1.0, st) - 0.5 + up) * Hh, 0.0024))
            rad.append(0.0016 if ext < 0.1 else 0.0006)
        mb.tube(pts, rad, lash, seg=8, flat=0.55)
        if st == 'cute':
            # 目じりの長いまつ毛 2 本
            for a0, up in ((0.82, 0.16), (0.93, 0.1)):
                b0 = on(cx + s_ * (a0 - 0.5) * W, cz + (face.lid_top(a0, st) - 0.5) * Hh + 0.001, 0.0024)
                b1 = on(cx + s_ * (a0 + 0.08 - 0.5) * W, cz + (face.lid_top(a0, st) - 0.5 + up) * Hh, 0.003)
                mb.tube([b0, b1], [0.0011, 0.0003], lash, seg=6)
        # 下まつ毛（目じり側だけ細く）
        pts = [on(cx + s_ * (a - 0.5) * W, cz + (face.lid_bot(a, st) - 0.5) * Hh - 0.0006, 0.0018) for a in (0.5, 0.65, 0.8, 0.92, 1.0)]
        mb.tube(pts, [0.0003, 0.0006, 0.0008, 0.0008, 0.0004], lash, seg=6, flat=0.6)
        # 二重の線
        pts = [on(cx + s_ * (a - 0.5) * W, cz + (face.lid_top(a, st) - 0.5 + 0.17) * Hh, 0.0012) for a in (0.25, 0.4, 0.55, 0.7, 0.85)]
        mb.tube(pts, [0.0003, 0.0006, 0.0007, 0.0006, 0.0003], crease_m, seg=6, flat=0.5)
        # 眉（細く、目じりへ細くなる）
        pts = []
        for k in range(7):
            a = k / 6
            bx = s_ * (0.017 + a * 0.05)
            bz = 1.630 + 0.009 * math.sin(math.pi * a * 0.85) - a * 0.004 + (0.002 if fem else 0.0)
            pts.append(on(bx, bz, 0.0018))
        bw = 0.85 if fem else 1.15
        mb.tube(pts, [r * bw for r in (0.0018, 0.0028, 0.003, 0.0027, 0.0022, 0.0015, 0.0007)], brow, seg=6, flat=0.45)
    # 口（ほほえみ）と下くちびるの影
    pts = []
    for k in range(9):
        u = (k - 4) / 4
        pts.append(on(u * 0.0145, 1.547 + abs(u) ** 2 * 0.0032 - (1 - abs(u)) * 0.0004, 0.0008))
    mb.tube(pts, [0.0005, 0.0011, 0.0016, 0.0019, 0.002, 0.0019, 0.0016, 0.0011, 0.0005], mouth, seg=6, flat=0.55)
    if cfg.get('scar'):
        pts = [on(-0.06 + k * 0.006, 1.6 - k * 0.012, 0.0008) for k in range(5)]
        mb.tube(pts, [0.0006, 0.0012, 0.0013, 0.0011, 0.0005], mat(name + "_Scar", tuple(c * 0.7 for c in skin_c), 0.6), seg=6, flat=0.5)
    ob = mb.build(name + "_Face", COLL)
    objs.append(ob)
    # ほお紅
    bl_img = bpy.data.images.get("BlushImg") or face.blush_image("BlushImg")
    bl_m = face.tex_mat("Blush", bl_img, 0.6)
    if fem or cfg.get('blush', True):
        for s_ in (-1, 1):
            objs.append(face.surface_patch(surf, P, s_ * 0.053, 1.566, 0.042, 0.024, s_, bl_m, f"{name}_Blush{'L' if s_ > 0 else 'R'}", COLL,
                                           lift=0.0008, nu=8, nv=5))
    for o in objs:
        rig_rigid(o, 'head')
    return objs


# ------------------------------------------------------------------ 手（5 本の指）
def _basis_rot(x, y, z):
    return Matrix((x, y, z)).transposed().to_euler()


def build_hands(cfg):
    b = cfg.get('build', 'male')
    lw = 0.86 if b == 'female' else (1.0 if b != 'slim' else 0.9)
    m = cmat(cfg, 'glove') if cfg.get('gloves') else cmat(cfg, 'skin')
    palm_m = m
    if cfg.get('gloves') == 'fingerless':
        m = cmat(cfg, 'skin')
    mb = CMB()
    for s_ in (-1, 1):
        sd = 'L' if s_ > 0 else 'R'
        wr = Vector(BMAP[f'forearm.{sd}'][2])
        ht = Vector(BMAP[f'hand.{sd}'][2])
        hd = (ht - wr).normalized()
        inward = Vector((-s_, 0, 0))
        pn = (inward - hd * inward.dot(hd)).normalized()       # 手のひらの向き（体のほう）
        ac = hd.cross(pn).normalized()                          # 指の並ぶ向き
        if ac.dot(Vector((0, -1, 0))) < 0:                       # 親指側（前）を + に
            ac = -ac
        # 手のひら・親指の付け根のふくらみ
        mb.add('sphere', palm_m, loc=wr + hd * 0.044 - pn * 0.002, rot=_basis_rot(ac, hd, pn), scale=(0.036 * lw, 0.05, 0.017 * lw))
        mb.add('sphere', palm_m, loc=wr + hd * 0.034 + ac * 0.02 * lw + pn * 0.004, rot=_basis_rot(ac, hd, pn), scale=(0.018 * lw, 0.024, 0.013 * lw))
        # 4 本の指（人さし指が前）
        for off, L in ((0.026, 0.042), (0.009, 0.047), (-0.008, 0.044), (-0.024, 0.035)):
            base = wr + hd * 0.084 + ac * off * lw - pn * 0.002
            d = hd.copy()
            pts = [base - d * 0.01]
            p = base.copy()
            for frac, curl in ((0.45, 0.22), (0.3, 0.38), (0.25, 0.35)):
                d = (d * math.cos(curl) + pn * math.sin(curl)).normalized()
                p = p + d * L * frac
                pts.append(p.copy())
            rr = [0.0098 * lw, 0.0094 * lw, 0.0086 * lw, 0.0076 * lw]
            mb.tube(pts, rr, m, seg=10)
            mb.add('sphere', m, loc=pts[-1], scale=(0.0076 * lw, 0.0076 * lw, 0.0076 * lw), seg=10, rings=6)
            # 指の付け根の関節（こぶし）
            mb.add('sphere', m, loc=base - pn * 0.003, scale=(0.0105 * lw, 0.0105 * lw, 0.0105 * lw), seg=10, rings=6)
        # 親指
        base = wr + hd * 0.03 + ac * 0.03 * lw + pn * 0.008
        d = (hd * 0.55 + ac * 0.62 + pn * 0.4).normalized()
        pts = [base]
        p = base.copy()
        for Lk, curl in ((0.028, 0.25), (0.024, 0.35)):
            d = (d * math.cos(curl) + (hd * 0.4 + pn * 0.9).normalized() * math.sin(curl)).normalized()
            p = p + d * Lk
            pts.append(p.copy())
        mb.tube(pts, [0.0115 * lw, 0.0105 * lw, 0.0088 * lw], m, seg=10)
        mb.add('sphere', m, loc=pts[-1], scale=(0.0088 * lw, 0.0088 * lw, 0.0088 * lw), seg=10, rings=6)
    ob = mb.build(cfg['name'] + "_Hands", COLL)

    def wf(v):
        sd = 'L' if v.co.x > 0 else 'R'
        wr = Vector(BMAP[f'forearm.{sd}'][2])
        if (v.co - wr).length < 0.015:
            return {f'hand.{sd}': 0.6, f'forearm.{sd}': 0.4}
        return {f'hand.{sd}': 1.0}
    assign_vgroups(ob, wf)
    return ob


# ------------------------------------------------------------------ チュニックのすそ（ひだのある布）
def build_tunic_skirt(cfg):
    if not cfg.get('tunic_flare') or cfg.get('robe') or cfg.get('dress'):
        return []
    tl = cfg.get('tunic_len', 0.8)
    m = cmat(cfg, 'top')
    prof = [(0.978, 0.146), (0.95, 0.152), (0.90, 0.168), (0.85, 0.184), (tl + 0.02, 0.198), (tl - 0.025, 0.206)]
    folds, amp = 12, 0.045
    seg = 72
    verts, faces = [], []
    for i, (z, r) in enumerate(prof):
        u = i / (len(prof) - 1)
        for k in range(seg):
            a = k / seg * math.tau
            rr = r * (1 + amp * u ** 1.4 * math.sin(a * folds + 0.5))
            verts.append((math.sin(a) * rr, 0.006 - math.cos(a) * rr * 0.74, z))
    for i in range(len(prof) - 1):
        for k in range(seg):
            a = i * seg + k
            b = i * seg + (k + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    mb = CMB()
    mb.poly(verts, faces, m, smooth=True)
    inner = mat(cfg['name'] + "_Lining", tuple(c * 0.5 for c in cfg['colors'].get('top', (0.5, 0.5, 0.5))), 0.9)
    mb.poly([(x * 0.985, y * 0.985, z) for (x, y, z) in verts], [tuple(reversed(f)) for f in faces], inner, smooth=True)
    # すその折り返し
    zb, rb = prof[-1]
    pts = []
    for k in range(seg * 2 + 1):
        a = k / (seg * 2) * math.tau
        rr = rb * (1 + amp * math.sin(a * folds + 0.5)) + 0.002
        pts.append(Vector((math.sin(a) * rr, 0.006 - math.cos(a) * rr * 0.74, zb + 0.006)))
    trim = cmat(cfg, 'belt') if cfg['name'] != 'Hero' else mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    mb.tube(pts, [0.0065] * len(pts), trim, seg=8, flat=1.3)
    ob = mb.build(cfg['name'] + "_Skirt", COLL)
    zt = prof[0][0]

    def wf(v):
        u = max(0.0, min(1.0, (zt - v.co.z) / (zt - zb)))
        wl = 0.55 * u ** 1.2
        if abs(v.co.x) < 0.03:
            return {'hips': 1 - wl, 'thigh.L': wl / 2, 'thigh.R': wl / 2}
        return {'hips': 1 - wl, ('thigh.L' if v.co.x > 0 else 'thigh.R'): wl}
    assign_vgroups(ob, wf)
    return [ob]


# ------------------------------------------------------------------ 服のふち（袖口・手袋の折り返し・ブーツの口・襟）
def limb_ring(mb, surf, a, b, t, add, r_tube, m, n=36, flat=1.4):
    a, b = Vector(a), Vector(b)
    c = a.lerp(b, t)
    ax = (b - a).normalized()
    u = ax.cross(Vector((0, 1, 0)))
    if u.length < 1e-3:
        u = ax.cross(Vector((1, 0, 0)))
    u.normalize()
    v = ax.cross(u).normalized()
    pts = []
    for k in range(n + 1):
        ang = k / n * math.tau
        d = u * math.cos(ang) + v * math.sin(ang)
        hit, nn = surf.ray(c, d, 0.2)
        if hit is None:
            hit = c + d * 0.045
        pts.append(hit + d * add)
    mb.tube(pts, [r_tube] * len(pts), m, seg=8, flat=flat)


def build_trims(cfg, surf):
    mb = CMB()
    any_ = False
    sl = cfg.get('sleeves', 'long')
    for sd in ('L', 'R'):
        ua, fa, sh = BMAP[f'upper_arm.{sd}'], BMAP[f'forearm.{sd}'], BMAP[f'shin.{sd}']
        if 'under' in cfg['colors']:
            limb_ring(mb, surf, ua[1], ua[2], 0.06, 0.004, 0.0065, mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0))
            any_ = True
        elif sl != 'long' and not cfg.get('robe'):
            t = 0.6 if sl == 'short' else 0.12
            limb_ring(mb, surf, ua[1], ua[2], t, 0.003, 0.0075, cmat(cfg, 'top'))
            any_ = True
        if cfg.get('gloves'):
            # 手袋の口は外へ少し開いた二重の折り返し
            limb_ring(mb, surf, fa[1], fa[2], 0.42, 0.006, 0.009, cmat(cfg, 'glove'), flat=1.6)
            limb_ring(mb, surf, fa[1], fa[2], 0.36, 0.009, 0.007, cmat(cfg, 'glove'), flat=1.6)
            any_ = True
        elif sl == 'long' and not cfg.get('robe'):
            limb_ring(mb, surf, fa[1], fa[2], 0.9, 0.003, 0.0065, cmat(cfg, 'top'))
            any_ = True
        if cfg.get('boots', True) and not cfg.get('robe'):
            bh = cfg.get('boot_h', 0.33)
            a, b = Vector(sh[1]), Vector(sh[2])
            t = (a.z - bh) / (a.z - b.z)
            if 0 < t < 1:
                limb_ring(mb, surf, a, b, t, 0.007, 0.012, cmat(cfg, 'boot'), flat=1.5)
                limb_ring(mb, surf, a, b, t - 0.05, 0.004, 0.008, cmat(cfg, 'boot'), flat=1.5)
                any_ = True
    # 襟
    if not cfg.get('armor'):
        # 首の付け根にそった襟（遠くの肩まで届いた点は首の太さで止める）
        c0 = Vector((0, 0.004, 1.428))
        pts = []
        for k in range(41):
            ang = k / 40 * math.tau
            d = Vector((math.sin(ang), -math.cos(ang), 0.0))
            hit, nn = surf.ray(c0, d, 0.12)
            dist = (hit - c0).length if hit is not None else 0.06
            dist = min(dist, 0.058 if abs(math.sin(ang)) < 0.6 else 0.064)
            front = max(0.0, math.cos(ang))
            pts.append(c0 + d * (dist + 0.004) + Vector((0, 0, -0.012 * front)))
        mb.tube(pts, [0.0075] * len(pts), cmat(cfg, 'top'), seg=8, flat=1.5)
        any_ = True
    if not any_:
        return []
    ob = mb.build(cfg['name'] + "_Trims", COLL)
    assign_vgroups(ob, lambda v: weights_for(v.co, cfg))
    return [ob]


def _merge_cmb(dst, src):
    """CMB src の面を dst に移す（材質番号も合わせる）"""
    import bmesh as _bm
    vm = {}
    for v in src.bm.verts:
        vm[v] = dst.bm.verts.new(v.co)
    for f in src.bm.faces:
        try:
            nf = dst.bm.faces.new([vm[v] for v in f.verts])
        except ValueError:
            continue
        nf.material_index = dst._mi(src.mats[f.material_index])
        nf.smooth = f.smooth


# ------------------------------------------------------------------ 髪
def build_hair(cfg, surf):
    """頭の形に沿って流れる平たい毛束を重ねて髪型を作る"""
    style = cfg.get('hair', 'short')
    if style in ('none', 'helmet'):
        return []
    if style == 'twintails':
        pass
    hs = cfg.get('head_scale', 0.98)
    hair_m = cmat(cfg, 'hair')
    rng = random.Random(sum(map(ord, cfg['name'])))

    def P(p):
        return HEAD_PIVOT + (Vector(p) - HEAD_PIVOT) * hs

    C = Vector((0, 0.012, 1.628))
    RX, RY, RZ = 0.101, 0.111, 0.114

    def S(th, ph, k=1.0):
        return C + Vector((math.sin(ph) * math.sin(th) * RX * k, -math.sin(ph) * math.cos(th) * RY * k, math.cos(ph) * RZ * k))

    def outward(th, ph):
        return Vector((math.sin(ph) * math.sin(th) / RX, -math.sin(ph) * math.cos(th) / RY, math.cos(ph) / RZ)).normalized()

    out = []
    # 下地（頭皮を覆うキャップ）
    if style == 'turban':
        elems = [E_ell((0, 0.012, 1.672), 0.114, 0.124, 0.098), E_ell((0, 0.02, 1.73), 0.09, 0.1, 0.06)]
        cap_m = cmat(cfg, 'hat')
    elif style == 'bald':
        elems = [E_ell((s * 0.088, 0.04, 1.598), 0.022, 0.05, 0.036) for s in (-1, 1)] + [E_ell((0, 0.09, 1.598), 0.068, 0.028, 0.04)]
        cap_m = hair_m
    else:
        elems = [E_ell(C + Vector((0, 0.004, 0.006)), RX * 0.985, RY * 0.985, RZ * 0.97)]
        if style == 'long' and not cfg.get('braids'):
            elems += [E_ell((0, 0.07, 1.50), 0.1, 0.05, 0.14), E_ell((0, 0.074, 1.39), 0.094, 0.04, 0.09)]
        cap_m = hair_m
    me = meta_mesh(cfg['name'] + "_Hair", [head_xf(e, hs) for e in elems], res=0.006)
    me = decimate(me, 4000)
    cap = mesh_to_obj(me, cfg['name'] + "_Hair")
    cap.data.materials.append(cap_m)
    rig_hair(cap)
    out.append(cap)

    mb = CMB()

    def hair_lock(pts, nrm, rad, flat, seg=10):
        """三日月形の断面の毛束（中央がふくらみ、両端は頭に沿って内へ）"""
        verts, faces = [], []
        n = len(pts)
        for i in range(n):
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            nn = (nrm[i] - t * nrm[i].dot(t))
            nn = nn.normalized() if nn.length > 1e-6 else Vector((0, 0, 1))
            sd = t.cross(nn).normalized()
            w = rad[i]
            th_ = w * max(flat, 0.3)
            for k in range(seg):
                a_ = k / seg * math.tau
                x = math.cos(a_)
                off = sd * x * w + nn * (math.sin(a_) * th_ * 0.6 + (1 - x * x) * w * 0.3 - w * 0.08)
                verts.append(tuple(pts[i] + off))
        for i in range(n - 1):
            for k in range(seg):
                a0 = i * seg + k
                b0 = i * seg + (k + 1) % seg
                faces.append((a0, a0 + seg, b0 + seg, b0))
        tip = pts[-1] + (pts[-1] - pts[-2]).normalized() * rad[-1] * 2
        verts.append(tuple(tip))
        root = pts[0] - (pts[1] - pts[0]).normalized() * rad[0] * 0.5
        verts.append(tuple(root))
        ti, ri = len(verts) - 2, len(verts) - 1
        for k in range(seg):
            faces.append(((n - 1) * seg + k, ti, (n - 1) * seg + (k + 1) % seg))
            faces.append((ri, k, (k + 1) % seg))
        mb.poly(verts, faces, hair_m, smooth=True)

    def clump(th, ph0, ph1, width, ext=0.0, lift=0.0, droop=0.0, flat=0.42, twist=0.0, tail_down=0.0, steps=7, split=True, rise=0.0):
        pts, rad = [], []
        for i in range(steps):
            u = i / (steps - 1)
            ph = ph0 + (ph1 - ph0) * u
            t = th + twist * u
            p = S(t, ph, 1.0 + 0.02 * math.sin(u * math.pi) + rise * u ** 1.6)
            pts.append(p)
        nrm = [outward(th + twist * (i / (steps - 1)), ph0 + (ph1 - ph0) * (i / (steps - 1))) for i in range(steps)]
        n_end = outward(th + twist, ph1)
        last = pts[-1]
        tang = (pts[-1] - pts[-2]).normalized()
        for j in range(1, 5):
            v = j / 4
            q = last + (tang * (1 - lift) + n_end * lift).normalized() * ext * v + Vector((0, 0, -droop * v * v - tail_down * v))
            pts.append(q)
            nrm.append(n_end)
        n = len(pts)
        for i in range(n):
            u = i / (n - 1)
            rad.append(width * (0.55 + 0.9 * math.sin(min(u * 1.6, 1.0) * math.pi * 0.5)) * (1 - u) ** 0.85 + 0.0009)
        hair_lock([P(q) for q in pts], nrm, [r * hs for r in rad], flat)
        # 太い束は 2 本の細い束に分けて、毛先がばらける
        if split and width > 0.024 and ext > 0.012:
            for sgn in (-1, 1):
                sd = tang.cross(n_end).normalized()
                off = sd * width * 0.3 * sgn
                pts2 = [q + off * (k / (n - 1)) ** 2 for k, q in enumerate(pts)]
                pts2[-1] = pts2[-1] + sd * width * 0.25 * sgn + Vector((0, 0, -0.004))
                hair_lock([P(q) for q in pts2[n // 2:]], nrm[n // 2:], [r * hs * 0.55 for r in rad[n // 2:]], flat)

    if style == 'twintails':
        # 前髪と、頭に沿った短めの横・後ろ
        for i in range(13):
            u = i / 12 * 2 - 1
            th = u * math.radians(50)
            end = 1.38 + (0.07 if abs(u) < 0.35 else 0.0) - abs(u) * 0.04 + rng.uniform(-0.02, 0.02)
            clump(th, 0.12, end, 0.023, ext=0.02, lift=0.18, droop=0.005, twist=-u * 0.25 + rng.uniform(-0.06, 0.06), split=False)
        for i in range(26):
            th = math.radians(58 + i / 25 * 244) + rng.uniform(-0.04, 0.04)
            clump(th, 0.1, 1.8 + 0.2 * max(-math.cos(th), 0), 0.03, ext=0.015, lift=0.1, droop=0.004, split=False)
        for s_ in (-1, 1):
            clump(s_ * math.radians(78), 0.5, 2.2, 0.02, ext=0.06, lift=0.0, tail_down=0.05, split=False)
        # 左右の高い位置で結んだ房
        for s_ in (-1, 1):
            T = S(s_ * math.radians(112), 1.45, 1.03)
            for j in range(12):
                ang = j / 12 * math.tau
                off = Vector((math.cos(ang) * 0.02 * s_, math.sin(ang) * 0.02, 0))
                pts = [T + off * 0.4]
                ctr = [T]
                for k, (dx, dy, dz) in enumerate(((0.06, 0.03, 0.0), (0.1, 0.05, -0.08), (0.11, 0.06, -0.2), (0.09, 0.05, -0.32), (0.06, 0.04, -0.42), (0.035, 0.03, -0.48))):
                    spread = 1.0 + 0.9 * min(k, 3) / 3
                    q = T + Vector((s_ * dx, dy, dz)) + off * spread + Vector((rng.uniform(-1, 1) * 0.006, 0, rng.uniform(-1, 1) * 0.01))
                    pts.append(q)
                    ctr.append(T + Vector((s_ * dx, dy, dz)))
                nrm = [((pp - cc) if (pp - cc).length > 1e-5 else Vector((s_, 0, 0))).normalized() for pp, cc in zip(pts, ctr)]
                n = len(pts)
                rad = [0.028 * (0.7 + 0.5 * math.sin(min(k / (n - 1) * 1.8, 1.0) * math.pi * 0.5)) * (1 - k / n) ** 0.65 + 0.001 for k in range(n)]
                hair_lock([P(q) for q in pts], nrm, [r * hs for r in rad], 0.9)
            rib = mat(cfg['name'] + "_Ribbon", cfg['colors'].get('ribbon', (1, 0.4, 0.55)), 0.5)
            make_bow(mb, P(T + Vector((s_ * 0.012, -0.005, 0.012))), Vector((0, -1, 0.2)), Vector((s_ * 0.3, 0, 1)), 0.045 * hs, rib, tails=True)
    if style in ('spiky', 'short', 'long'):
        # 前髪
        nb = 13 if style != 'short' else 10
        if style == 'spiky':
            nb = 0
            for i in range(7):
                u = i / 6 * 2 - 1
                th = u * math.radians(55) + rng.uniform(-0.05, 0.05)
                end = 1.3 + (0.12 if abs(u) < 0.4 else 0.04) * rng.uniform(0.6, 1.2) - abs(u) * 0.1
                clump(th, 0.2, end, 0.042, ext=0.035, lift=0.25, droop=0.004, twist=-u * 0.35 + rng.uniform(-0.08, 0.08),
                      flat=0.62, split=False)
            for i in range(10):
                u = i / 9 * 2 - 1
                th = u * math.radians(48)
                clump(th, 0.6 + rng.uniform(-0.05, 0.05), -0.45 - 0.35 * (1 - abs(u)) + rng.uniform(-0.1, 0.1), 0.05,
                      ext=0.05 + 0.04 * (1 - abs(u)) + rng.uniform(0, 0.03), lift=0.45, droop=-0.01, flat=0.75, split=False,
                      twist=u * 0.4, steps=9, rise=0.28 + 0.12 * (1 - abs(u)))
        for i in range(nb):
            u = i / (nb - 1) * 2 - 1
            th = u * math.radians(48)
            end = 1.42 + (0.06 if abs(u) < 0.3 else 0.0) - abs(u) * 0.05 + rng.uniform(-0.03, 0.03)
            clump(th, 0.12, end, 0.026 if style == 'spiky' else 0.022, ext=0.03 if style != 'short' else 0.015,
                  lift=0.15, droop=0.006, twist=-u * 0.25 + rng.uniform(-0.08, 0.08), split=False)
        # 横・後ろ
        ring = 30
        for i in range(ring):
            th = math.radians(55 + i / (ring - 1) * 250) + rng.uniform(-0.05, 0.05)
            back = -math.cos(th)  # 後ろほど 1
            if style == 'spiky':
                clump(th, 0.1, 1.7 + 0.35 * max(back, 0), 0.046, ext=0.06 + 0.05 * max(back, 0), lift=0.6,
                      droop=-0.01, twist=rng.uniform(-0.12, 0.12), flat=0.62, split=False, rise=0.1)
            elif style == 'short':
                clump(th, 0.1, 1.85 + 0.25 * max(back, 0), 0.03, ext=0.02, lift=0.1, droop=0.005)
            else:
                clump(th, 0.1, 2.0, 0.032, ext=0.12 + 0.12 * max(back, 0), lift=0.05, droop=0.02,
                      tail_down=0.08 + 0.1 * max(back, 0), twist=rng.uniform(-0.05, 0.05))
        # 頭頂のツンツン
        if style == 'spiky':
            for i in range(5):
                th = math.radians(140 + i * 20 + rng.uniform(-6, 6))
                clump(th, 0.3, 1.1 + rng.uniform(0, 0.2), 0.05, ext=0.06 + rng.uniform(0, 0.04), lift=0.55,
                      droop=-0.02, flat=0.7, split=False, twist=rng.uniform(-0.1, 0.1), rise=0.2)
            for s in (-1, 1):
                clump(s * math.radians(80), 0.6, 2.1, 0.022, ext=0.025, lift=-0.1, droop=0.012, flat=0.5)
        if style == 'long' and cfg.get('braids'):
            # 顔の横の三つ編み（左右）
            for s_ in (-1, 1):
                top = S(s_ * math.radians(70), 1.7, 1.03)
                prev = None
                for k in range(24):
                    q = top + Vector((s_ * 0.006 * math.sin(k * 0.35), -0.012 - 0.002 * k, -0.021 * k))
                    sx = 1 if k % 2 == 0 else -1
                    q2 = q + Vector((sx * 0.0055, 0, 0))
                    w = 1 - k * 0.012
                    mb.add('sphere', hair_m, loc=P(q2), rot=(0, sx * 0.62, 0), scale=(0.0115 * hs * w, 0.012 * hs * w, 0.021 * hs), seg=12, rings=8)
                    prev = q
                tie = mat(cfg['name'] + "_Ribbon", cfg['colors'].get('ribbon', (0.3, 0.5, 0.9)), 0.5)
                mb.add('cyl', tie, loc=P(prev + Vector((0, 0, -0.02))), r1=0.011 * hs, r2=0.011 * hs, depth=0.012, seg=12)
                mb.tube([P(prev + Vector((0, 0, -0.026))), P(prev + Vector((s_ * 0.008, 0, -0.06)))], [0.012 * hs, 0.004 * hs], hair_m, seg=10)
        elif style == 'long':
            for s in (-1, 1):
                clump(s * math.radians(60), 0.35, 1.9, 0.026, ext=0.16, lift=0.0, tail_down=0.06)
            if cfg.get('flower'):
                # 花の髪飾り（5 枚の花びら）
                fc = S(-math.radians(62), 0.62, 1.04)
                pet = mat("Petal", cfg['flower'], 0.6)
                for k in range(5):
                    a = k / 5 * math.tau
                    mb.add('sphere', pet, loc=P(fc + Vector((-0.004, math.cos(a) * 0.014, math.sin(a) * 0.014))), rot=(a, 0, 0),
                           scale=(0.005, 0.013 * hs, 0.009 * hs), seg=10, rings=6)
                mb.add('sphere', mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0), loc=P(fc + Vector((-0.008, 0, 0))), scale=(0.006, 0.006, 0.006), seg=8, rings=6)
            elif not cfg.get('braids'):
                rib = mat(cfg['name'] + "_Ribbon", cfg['colors'].get('ribbon', (1, 0.4, 0.55)), 0.5)
                make_bow(mb, P(Vector((0, 0.12, 1.69))), Vector((-1, 0, 0)), Vector((0, 0, 1)), 0.04 * hs, rib, tails=False)
    if style == 'turban':
        band = cmat(cfg, 'hatband')
        pts = []
        for k in range(33):
            a = k / 32 * math.tau
            pts.append(P((math.sin(a) * 0.118, 0.012 - math.cos(a) * 0.128, 1.655)))
        mb.tube(pts, [0.014] * len(pts), band, seg=10)
        mb.add('sphere', cmat(cfg, 'gem'), loc=P((0, -0.126, 1.67)), scale=(0.014, 0.008, 0.018))
    if mb.bm.verts:
        ob = mb.build(cfg['name'] + "_HairStrands", COLL)
        rig_hair(ob)
        out.append(ob)
    return out


def rig_hair(ob):
    def wf(v):
        z = v.co.z
        w = smoothstep(1.36, 1.52, z)
        if w > 0.99:
            return {'head': 1.0}
        return {'head': w, 'chest': 1 - w} if w > 0.01 else {'chest': 1.0}
    assign_vgroups(ob, wf)


def lock_mesh(mb, pts, nrm, rad, flat, m, seg=10):
    """三日月形の断面の毛束（髪・ひげ共通）"""
    verts, faces = [], []
    n = len(pts)
    for i in range(n):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        nn = (nrm[i] - t * nrm[i].dot(t))
        nn = nn.normalized() if nn.length > 1e-6 else Vector((0, 0, 1))
        sd = t.cross(nn).normalized()
        w = rad[i]
        th_ = w * max(flat, 0.3)
        for k in range(seg):
            a_ = k / seg * math.tau
            x = math.cos(a_)
            off = sd * x * w + nn * (math.sin(a_) * th_ * 0.6 + (1 - x * x) * w * 0.3 - w * 0.08)
            verts.append(tuple(pts[i] + off))
    for i in range(n - 1):
        for k in range(seg):
            a0 = i * seg + k
            b0 = i * seg + (k + 1) % seg
            faces.append((a0, a0 + seg, b0 + seg, b0))
    tip = pts[-1] + (pts[-1] - pts[-2]).normalized() * rad[-1] * 2
    root = pts[0] - (pts[1] - pts[0]).normalized() * rad[0] * 0.5
    verts += [tuple(tip), tuple(root)]
    ti, ri = len(verts) - 2, len(verts) - 1
    for k in range(seg):
        faces.append(((n - 1) * seg + k, ti, (n - 1) * seg + (k + 1) % seg))
        faces.append((ri, k, (k + 1) % seg))
    mb.poly(verts, faces, m, smooth=True)


def build_beard(cfg, surf):
    """あごのラインから下へ流れる毛束のひげ（口のまわりは空ける）＋口ひげ"""
    kind = cfg.get('beard')
    if not kind:
        return []
    hs = cfg.get('head_scale', 0.98)
    bm_ = cmat(cfg, 'beard')
    rng = random.Random(sum(map(ord, cfg['name'])) + 5)

    def P(p):
        return HEAD_PIVOT + (Vector(p) - HEAD_PIVOT) * hs
    C = P((0, -0.01, 1.575))
    mb = CMB()
    # あごの下を埋める薄い土台（すき間から首が見えないように）
    el = [head_xf(E_ell((0, -0.055, 1.522), 0.05, 0.04, 0.026), hs)]
    for s_ in (-1, 1):
        el.append(head_xf(E_ell((s_ * 0.06, -0.035, 1.548), 0.02, 0.03, 0.03), hs))
    if kind == 'long':
        el.append(head_xf(E_ell((0, -0.075, 1.47), 0.045, 0.03, 0.06), hs))
    me = meta_mesh(cfg['name'] + "_Beard", el, res=0.006)
    me = decimate(me, 2500)
    base = mesh_to_obj(me, cfg['name'] + "_Beard")
    base.data.materials.append(bm_)
    longk = 1.0 if kind == 'long' else 0.0
    n = 19
    for i in range(n):
        u = i / (n - 1) * 2 - 1                       # -1（右の耳）.. 1（左の耳）
        th = u * math.radians(82)
        front = math.cos(th)
        d = Vector((math.sin(th), -math.cos(th), -0.55 - 0.25 * front)).normalized()
        hit, nn = surf.ray(C, d, 0.3)
        if hit is None:
            continue
        nn = nn.normalized()
        L = (0.035 + 0.03 * front) + longk * (0.05 + 0.1 * front ** 2)
        down = Vector((0, 0, -1))
        pts, nrm = [hit - nn * 0.002], [nn]
        for k in range(1, 6):
            v = k / 5
            q = hit + (down * (0.75 + 0.25 * v) + nn * (0.35 - 0.5 * v) + Vector((0, -0.25 * front, 0))).normalized() * L * v
            q += Vector((rng.uniform(-1, 1) * 0.002, 0, 0))
            pts.append(q)
            nrm.append((nn + Vector((0, -front * 0.5, 0))).normalized())
        w = (0.012 + 0.006 * front) * hs
        rad = [w * (0.7 + 0.5 * math.sin(min(k / 5 * 1.7, 1.0) * math.pi * 0.5)) * (1 - k / 6) ** 0.7 + 0.0008 for k in range(6)]
        lock_mesh(mb, pts, nrm, rad, 0.45, bm_)
    # 口ひげ（鼻の下から左右へ、毛先は下がる）
    for s_ in (-1, 1):
        pts = [P((s_ * 0.004, -0.104, 1.566)), P((s_ * 0.02, -0.104, 1.561)), P((s_ * 0.036, -0.097, 1.552)),
               P((s_ * 0.05, -0.086, 1.538)), P((s_ * 0.058, -0.077, 1.522))]
        nrm = [Vector((s_ * 0.3, -1, 0.2)).normalized()] * len(pts)
        lock_mesh(mb, pts, nrm, [0.006 * hs, 0.009 * hs, 0.008 * hs, 0.005 * hs, 0.002 * hs], 0.5, bm_)
    ob2 = mb.build(cfg['name'] + "_Mustache", COLL)
    rig_hair(base)
    rig_hair(ob2)
    return [base, ob2]


# ------------------------------------------------------------------ 服・装備
def ring_around(surf, center, z_tilt, radius_add, r_tube, m, n=40, name=None, flat=1.0):
    pts = []
    for k in range(n + 1):
        a = k / n * math.tau
        p, nn = surf.radial(center, a, z_tilt)
        pts.append(p + nn * radius_add)
    mb = CMB()
    mb.tube(pts, [r_tube] * len(pts), m, seg=10, flat=flat)
    return mb


def build_cape(cfg):
    col = cfg.get('cape')
    if not col:
        return None
    cm = mat(cfg['name'] + "_Cape", col, 0.75, double=True)
    lining = cfg.get('cape_len', 0.48)
    cols, rows = 18, 16
    verts, faces = [], []
    for r in range(rows + 1):
        v = r / rows
        z = 1.40 - v * (1.40 - lining)
        for c in range(cols + 1):
            u = c / cols * 2 - 1
            w = 0.17 + v * 0.17
            x = u * w
            # 肩にかかる上端は首の後ろを回り込む
            y = 0.10 + v * 0.10 + (u * u) * (0.02 if v > 0.1 else -0.03) + math.sin(u * math.pi * 3 + 0.4) * 0.012 * v
            if v < 0.08:
                y -= (1 - v / 0.08) * (u * u) * 0.08
            verts.append((x, y, z))
    for r in range(rows):
        for c in range(cols):
            a = r * (cols + 1) + c
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    mb = CMB()
    mb.poly(verts, faces, cm, smooth=True)
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    for s in (-1, 1):
        mb.add('sphere', gold, loc=(s * 0.11, -0.04, 1.40), scale=(0.022, 0.012, 0.022))
    ob = mb.build(cfg['name'] + "_Cape", COLL)

    def wf(vv):
        z = vv.co.z
        v = (1.40 - z) / (1.40 - lining)
        if v < 0.12:
            return {'chest': 1.0}
        if v < 0.5:
            k = (v - 0.12) / 0.38
            return {'chest': 1 - k, 'cape.1': k}
        k = (v - 0.5) / 0.5
        return {'cape.1': 1 - k, 'cape.2': k}
    assign_vgroups(ob, wf)
    return ob


def build_robe(cfg):
    """ローブ・ドレス：ひだのある回転体の一枚布"""
    kind = 'robe' if cfg.get('robe') else ('dress' if cfg.get('dress') else None)
    if not kind:
        return []
    fat = 0.03 if cfg.get('build') == 'portly' else 0.0
    if kind == 'robe':
        prof = [(0.995, 0.150), (0.93, 0.168), (0.78, 0.192), (0.55, 0.225), (0.30, 0.255), (0.10, 0.278), (0.02, 0.285)]
        folds, amp = 9, 0.035
    else:
        prof = [(0.975, 0.138), (0.92, 0.158), (0.80, 0.195), (0.66, 0.232), (0.54, 0.258), (0.50, 0.262)]
        folds, amp = 11, 0.05
    prof = [(z, r + fat * (1 - (0.995 - z))) for z, r in prof]
    m = cmat(cfg, kind)
    mb = CMB()
    seg = 64
    verts, faces = [], []
    for i, (z, r) in enumerate(prof):
        u = i / (len(prof) - 1)
        for k in range(seg):
            a = k / seg * math.tau
            rr = r * (1 + amp * u ** 1.3 * math.sin(a * folds + u * 0.8))
            verts.append((math.sin(a) * rr, 0.012 - math.cos(a) * rr * 0.9, z))
    for i in range(len(prof) - 1):
        for k in range(seg):
            a = i * seg + k
            b = i * seg + (k + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    mb.poly(verts, faces, m, smooth=True)
    # 内側（裾からのぞいたときの裏地）
    inner = mat(cfg['name'] + "_Lining", tuple(c * 0.55 for c in cfg['colors'].get(kind, (0.5, 0.5, 0.5))), 0.9)
    mb.poly([(x * 0.985, y * 0.985, z) for (x, y, z) in verts], [tuple(reversed(f)) for f in faces], inner, smooth=True)
    zt, rt = prof[0]
    sash = cmat(cfg, 'sash') if 'sash' in cfg['colors'] else cmat(cfg, 'belt')
    pts = [Vector((math.sin(k / 48 * math.tau) * (rt + 0.006), 0.012 - math.cos(k / 48 * math.tau) * (rt + 0.006) * 0.9, zt - 0.01))
           for k in range(49)]
    mb.tube(pts, [0.017] * len(pts), sash, seg=10, flat=1.6)
    if kind == 'robe' and cfg.get('hem'):
        zb, rb = prof[-1]
        pts = [Vector((math.sin(k / 64 * math.tau) * rb, 0.012 - math.cos(k / 64 * math.tau) * rb * 0.9, zb + 0.03)) for k in range(65)]
        mb.tube(pts, [0.012] * len(pts), mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0), seg=8, flat=1.8)
    if kind == 'dress':
        zb, rb = prof[-1]
        pts = []
        for k in range(97):
            a = k / 96 * math.tau
            rr = rb * (1 + amp * math.sin(a * folds + 0.8)) + 0.006
            pts.append(Vector((math.sin(a) * rr, 0.012 - math.cos(a) * rr * 0.9, zb + 0.012 + 0.006 * math.sin(a * 22))))
        mb.tube(pts, [0.014] * len(pts), mat("Frill", (1.0, 0.97, 0.95), 0.8), seg=8, flat=1.4)
    ob = mb.build(cfg['name'] + "_" + kind.capitalize(), COLL)

    def wf(v):
        z = v.co.z
        u = max(0.0, min(1.0, (zt - z) / (zt - 0.02)))
        wl = (0.45 if kind == 'robe' else 0.6) * u
        side = 'thigh.L' if v.co.x > 0 else 'thigh.R'
        if abs(v.co.x) < 0.04:
            return {'hips': 1 - wl, 'thigh.L': wl / 2, 'thigh.R': wl / 2}
        return {'hips': 1 - wl, side: wl}
    assign_vgroups(ob, wf)
    return [ob]


def shell_rims(bm, thickness, rim_m, r_tube):
    """殻の外周（境界の辺）にそって巻きふちのチューブを作る"""
    bnd = [e for e in bm.edges if e.is_boundary]
    adj = {}
    for e in bnd:
        a, b = e.verts
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    seen = set()
    mb = CMB()
    for start in list(adj.keys()):
        if start in seen:
            continue
        chain = [start]
        seen.add(start)
        cur, prev = start, None
        while True:
            nxt = [v for v in adj[cur] if v is not prev and v not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            chain.append(cur)
            seen.add(cur)
        if len(chain) < 4:
            continue
        closed = start in adj[chain[-1]]
        pts = [v.co + v.normal * (thickness * 0.5) for v in chain]
        for _ in range(12):
            m_ = len(pts)
            pts = [pts[i] if (not closed and i in (0, m_ - 1)) else pts[i] * 0.5 + (pts[(i - 1) % m_] + pts[(i + 1) % m_]) * 0.25 for i in range(m_)]
        # 細かすぎる点を間引いてなめらかに
        step = max(1, len(pts) // 60)
        pts = pts[::step]
        if closed:
            pts.append(pts[0])
        mb.tube(pts, [r_tube] * len(pts), rim_m, seg=8, flat=1.3)
    return mb


def build_shell(cfg, body_ob, region_fn, thickness, m, name, solid=0.006, rim=None, rim_r=0.006):
    """体の表面から一部を抜き出して服・鎧の層を作る（体にぴったり沿う）。rim があれば外周に巻きふち"""
    me = body_ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    keep = [f for f in bm.faces if region_fn(f.calc_center_median())]
    keepset = set(keep)
    kill = [f for f in bm.faces if f not in keepset]
    bmesh.ops.delete(bm, geom=kill, context='FACES_ONLY')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    for v in bm.verts:
        v.co += v.normal * thickness
    rim_ob = None
    if rim is not None:
        bm.normal_update()
        rmb = shell_rims(bm, 0.0, rim, rim_r)
        if rmb.bm.verts:
            rim_ob = rmb.build(name + "Rim", COLL)
            assign_vgroups(rim_ob, lambda v: weights_for(v.co, cfg))
    nme = bpy.data.meshes.new(name)
    bm.to_mesh(nme)
    bm.free()
    nme.validate()
    nme.materials.clear()
    nme.materials.append(m)
    for p in nme.polygons:
        p.material_index = 0
    ob = bpy.data.objects.new(name, nme)
    COLL.objects.link(ob)
    if solid:
        mod = ob.modifiers.new("solid", 'SOLIDIFY')
        mod.thickness = solid
        mod.offset = -1
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        m2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        old = ob.data
        ob.data = m2
        bpy.data.meshes.remove(old)
        m2.validate()
        m2.name = name
    ob.data.shade_smooth()
    assign_vgroups(ob, lambda v: weights_for(v.co, cfg))
    if rim is not None:
        return [ob] + ([rim_ob] if rim_ob else [])
    return ob


HOLD_BEND = 1.2   # 武器を持つ右ひじの曲げ（src/actors/actor.js と同じ値）


def build_gear(cfg, surf):
    name = cfg['name']
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    silver = mat("Silver", (0.85, 0.87, 0.92), 0.25, 1.0)
    wood = mat("Wood", (0.42, 0.27, 0.14), 0.8)
    leather = mat("Leather", (0.30, 0.18, 0.10), 0.6)
    hs = cfg.get('head_scale', 0.98)
    out = []

    def P(p):
        return HEAD_PIVOT + (Vector(p) - HEAD_PIVOT) * hs

    # 胸元の編み上げひも（チュニック）
    if cfg.get('lacing'):
        lm = cmat(cfg, 'belt')
        mb = CMB()
        zs = [1.405 - k * 0.022 for k in range(5)]
        pts = []
        for k, z in enumerate(zs):
            for sx in ((-1, 1) if k % 2 == 0 else (1, -1)):
                q, nn = surf.front(sx * 0.016, z)
                pts.append(q + nn * 0.004)
        mb.tube(pts, [0.0024] * len(pts), lm, seg=6)
        for z in zs:
            for sx in (-1, 1):
                q, nn = surf.front(sx * 0.016, z)
                mb.add('sphere', gold, loc=q + nn * 0.003, scale=(0.0042, 0.0042, 0.0042), seg=8, rings=5)
        q, nn = surf.front(0, zs[-1] - 0.01)
        mb.tube([q + nn * 0.004, q + nn * 0.006 + Vector((0.008, 0, -0.035)), q + nn * 0.006 + Vector((0.004, 0, -0.06))], [0.0024, 0.0022, 0.0018], lm, seg=6)
        ob = mb.build(name + "_Lacing", COLL)
        rig_rigid(ob, 'chest')
        out.append(ob)
    # ベルト
    if not cfg.get('robe') and not cfg.get('dress'):
        mb = ring_around(surf, (0, 0.004, 0.963), 0.0, 0.002, 0.016, cmat(cfg, 'belt'), flat=1.6)
        p, n = surf.front(0, 0.963)
        mb.add('cube', gold, loc=p + n * 0.012, rot=basis_euler(n), scale=(0.05, 0.012, 0.04))
        mb.add('cube', cmat(cfg, 'belt'), loc=p + n * 0.016, rot=basis_euler(n), scale=(0.03, 0.01, 0.022))
        ob = mb.build(name + "_Belt", COLL)
        rig_rigid(ob, 'hips')
        out.append(ob)
    # ヘアバンド
    if cfg.get('headband'):
        mb = CMB()
        bandm = mat(name + "_Band", cfg['headband'], 0.7)
        pts = []
        for k in range(49):
            a = k / 48 * math.tau
            back = (1 - math.cos(a)) * 0.5
            q = P((math.sin(a) * 0.109, 0.012 - math.cos(a) * 0.12, 1.648 + back * 0.035))
            pts.append(q)
        mb.tube(pts, [0.0075 * hs] * len(pts), bandm, seg=10, flat=1.5)
        knot = P((0, 0.13, 1.682))
        mb.add('sphere', bandm, loc=knot, scale=(0.014, 0.012, 0.012))
        for s_ in (-1, 1):
            mb.tube([knot, knot + Vector((s_ * 0.025, 0.02, -0.04)), knot + Vector((s_ * 0.035, 0.035, -0.1))], [0.009, 0.008, 0.003],
                    bandm, seg=8, flat=0.35)
        ob = mb.build(name + "_Headband", COLL)
        rig_rigid(ob, 'head')
        out.append(ob)
    # 王冠
    if cfg.get('crown'):
        mb = CMB()
        cz = 1.735
        mb.add('cyl', gold, loc=P((0, 0.02, cz)), r1=0.074 * hs, r2=0.08 * hs, depth=0.035 * hs, seg=32)
        for k in range(8):
            a = k / 8 * math.tau
            mb.add('cyl', gold, loc=P((math.sin(a) * 0.075, 0.02 - math.cos(a) * 0.075, cz + 0.035)), r1=0.014 * hs, r2=0.0, depth=0.04 * hs, seg=8)
            mb.add('sphere', mat("Ruby", (0.9, 0.05, 0.1), 0.1), loc=P((math.sin(a) * 0.079, 0.02 - math.cos(a) * 0.079, cz)), scale=(0.006, 0.006, 0.006))
        mb.add('sphere', mat("Velvet", (0.6, 0.05, 0.12), 0.9), loc=P((0, 0.02, cz + 0.015)), scale=(0.07 * hs, 0.07 * hs, 0.04 * hs))
        ob = mb.build(name + "_Crown", COLL)
        rig_rigid(ob, 'head')
        out.append(ob)
    # 魔女の帽子（ミリア）
    if cfg.get('witch_hat'):
        mb = CMB()
        hm = mat(name + "_Hat", cfg['witch_hat'], 0.8)
        # 波打つ大きなつば
        verts, faces = [], []
        seg = 48
        for r_, (rad, dz) in enumerate(((0.10, 0.0), (0.17, -0.004), (0.235, -0.012), (0.26, -0.02))):
            for k in range(seg):
                a = k / seg * math.tau
                w = 0.012 * math.sin(a * 3) * (r_ / 3)
                verts.append(P((math.sin(a) * rad, 0.01 - math.cos(a) * rad, 1.718 + dz + w + (0.012 if r_ == 3 and math.cos(a) > 0.3 else 0))))
        for r_ in range(3):
            for k in range(seg):
                i0 = r_ * seg + k
                i1 = r_ * seg + (k + 1) % seg
                faces.append((i0, i1, i1 + seg, i0 + seg))
        mb.poly([tuple(v) for v in verts], faces, hm, smooth=True)
        mb.poly([tuple(Vector(v) + Vector((0, 0, -0.006))) for v in verts], [tuple(reversed(f)) for f in faces], hm, smooth=True)
        # 先が後ろへ折れる円すい
        mb.tube([P((0, 0.01, 1.70)), P((0, 0.02, 1.83)), P((0, 0.05, 1.94)), P((0, 0.11, 2.01)), P((0, 0.19, 2.02)), P((0, 0.25, 1.97)), P((0, 0.27, 1.92))],
                [0.122 * hs, 0.092 * hs, 0.064 * hs, 0.04 * hs, 0.024 * hs, 0.012 * hs, 0.003], hm, seg=20)
        ring = [P((math.sin(k / 40 * math.tau) * 0.121, 0.01 - math.cos(k / 40 * math.tau) * 0.121, 1.74)) for k in range(41)]
        mb.tube(ring, [0.014 * hs] * 41, mat("HatBand", (0.95, 0.75, 0.25), 0.4, 0.6), seg=8, flat=1.6)
        # 前の星のバックルと、先に下がる星
        glow = mat("MagicGlow", (0.75, 0.35, 1.0), 0.2, emit=(0.75, 0.30, 1.0), emit_strength=4.0)
        goldm = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)

        def star(c, rr, nrm_y=-1):
            pts = []
            for k in range(10):
                a = k / 10 * math.tau
                q = rr if k % 2 == 0 else rr * 0.45
                pts.append(tuple(c + Vector((math.sin(a) * q, 0, math.cos(a) * q))))
            ctr = c + Vector((0, nrm_y * rr * 0.35, 0))
            back = c + Vector((0, -nrm_y * rr * 0.25, 0))
            mb.poly([tuple(ctr)] + pts, [(0, i + 1, (i + 1) % 10 + 1) for i in range(10)], goldm)
            mb.poly([tuple(back)] + pts, [(0, (i + 1) % 10 + 1, i + 1) for i in range(10)], goldm)
        star(P((0, -0.118, 1.745)), 0.022 * hs)
        tipc = P((0, 0.27, 1.92))
        mb.tube([tipc, tipc + Vector((0, 0.01, -0.06))], [0.002, 0.002], goldm, seg=6)
        star(tipc + Vector((0, 0.01, -0.08)), 0.02 * hs)
        mb.add('ico', glow, loc=P((0, -0.124, 1.745)), r=0.007, sub=1)
        ob = mb.build(name + "_Hat", COLL)
        rig_rigid(ob, 'head')
        out.append(ob)
    # サークレット（セレナ）
    if cfg.get('circlet'):
        mb = CMB()
        ring = [P((math.sin(k / 40 * math.tau) * 0.104, 0.012 - math.cos(k / 40 * math.tau) * 0.114, 1.668 + 0.02 * math.cos(k / 40 * math.tau))) for k in range(41)]
        mb.tube(ring, [0.006 * hs] * 41, gold, seg=8, flat=1.4)
        mb.add('sphere', mat("Sapphire", (0.15, 0.35, 1.0), 0.1), loc=P((0, -0.118, 1.69)), scale=(0.016, 0.01, 0.022))
        ob = mb.build(name + "_Circlet", COLL)
        rig_rigid(ob, 'head')
        out.append(ob)
    # 兜
    if cfg.get('helmet'):
        mb = CMB()
        mb.add('sphere', silver, loc=P((0, 0.012, 1.672)), scale=(0.112 * hs, 0.122 * hs, 0.11 * hs), seg=32, rings=20)
        mb.add('cyl', silver, loc=P((0, 0.012, 1.628)), r1=0.121 * hs, r2=0.119 * hs, depth=0.022, seg=32)
        mb.add('cyl', gold, loc=P((0, 0.012, 1.64)), r1=0.12 * hs, r2=0.12 * hs, depth=0.008, seg=32)
        mb.add('cube', silver, loc=P((0, -0.12, 1.6)), scale=(0.012, 0.01, 0.06), bevel=0.003)
        mb.add('cube', gold, loc=P((0, -0.012, 1.74)), scale=(0.014, 0.25, 0.016), bevel=0.004)
        mb.tube([P((0, -0.08, 1.76)), P((0, 0.0, 1.8)), P((0, 0.09, 1.77)), P((0, 0.15, 1.66))], [0.016, 0.022, 0.02, 0.006],
                mat("Plume", (0.8, 0.08, 0.1), 0.8), seg=10)
        ob = mb.build(name + "_Helmet", COLL)
        rig_rigid(ob, 'head')
        out.append(ob)
    # 王のファーの襟
    if cfg.get('fur'):
        mb = CMB()
        pts = []
        for k in range(41):
            a = k / 40 * math.tau
            pts.append(Vector((math.sin(a) * 0.15, 0.01 - math.cos(a) * 0.115, 1.42 + 0.01 * math.cos(a))))
        mb.tube(pts, [0.038] * len(pts), mat("Fur", (0.97, 0.96, 0.92), 0.95), seg=12)
        mb.deform(lambda co: co + co.normalized() * 0.004 * noise.noise(co * 90))
        ob = mb.build(name + "_Collar", COLL)
        rig_rigid(ob, 'chest')
        out.append(ob)
    # 右手の武器
    hr_w = Vector(BMAP['forearm.R'][2])
    hd = (Vector(BMAP['hand.R'][2]) - hr_w).normalized()
    palm = hr_w + hd * 0.05
    # 杖・斧・槍は「ひじを前に曲げて握った姿勢」で縦にまっすぐ持つように作り、
    # 休めの姿勢（骨格の初期姿勢）に戻して手の骨に付ける。ゲーム側で同じ角度だけひじを曲げる（HOLD_BEND）
    el_w = Vector(BMAP['forearm.R'][1])
    hold_ax = (hr_w - el_w).normalized().cross(Vector((0, 1, 0))).normalized()
    hold_q = Quaternion(hold_ax, -HOLD_BEND)
    hpalm = el_w + hold_q @ (palm - el_w)
    unbend = hold_q.inverted()

    def held(mb):
        mb.deform(lambda co: el_w + unbend @ (Vector(co) - el_w))

    if cfg.get('sword'):
        mb = CMB()
        mb.add('cyl', leather, loc=palm, rot=(math.pi / 2, 0, 0), r1=0.014, r2=0.014, depth=0.11, seg=12)
        for k in range(6):
            mb.add('cyl', leather, loc=palm + Vector((0, -0.045 + k * 0.018, 0)), rot=(math.pi / 2, 0, 0), r1=0.0165, r2=0.0165, depth=0.008, seg=12)
        # 反った鍔（先が玉）と中央の宝石
        g0 = palm + Vector((0, -0.065, 0))
        for s in (-1, 1):
            mb.tube([g0, g0 + Vector((s * 0.05, 0.004, 0.006)), g0 + Vector((s * 0.085, 0.012, 0.022))], [0.016, 0.012, 0.009], gold, seg=10, flat=0.7)
            mb.add('sphere', gold, loc=g0 + Vector((s * 0.088, 0.013, 0.026)), scale=(0.014, 0.014, 0.014))
        mb.add('sphere', mat("Sapphire", (0.15, 0.35, 1.0), 0.1), loc=g0 + Vector((0, 0, 0.0)), scale=(0.012, 0.016, 0.012))
        blade = mat("Blade", (0.92, 0.94, 0.98), 0.12, 1.0, double=True)
        L = 0.78
        bv, bf = [], []
        prof = [(-0.022, 0), (0, 0.006), (0.022, 0), (0, -0.006)]
        for k, yy in enumerate((0.0, 0.85)):
            sc = 1.0 if k == 0 else 0.85
            for (px, pz) in prof:
                bv.append((palm.x + px * sc, palm.y - 0.08 - yy * L, palm.z + pz))
        bv.append((palm.x, palm.y - 0.08 - L, palm.z))
        for i in range(4):
            j = (i + 1) % 4
            bf.append((i, j, 4 + j, 4 + i))
            bf.append((4 + i, 4 + j, 8))
        bf.append((3, 2, 1, 0))
        mb.poly(bv, bf, blade, smooth=False)
        mb.add('sphere', mat("Sapphire", (0.15, 0.35, 1.0), 0.1), loc=palm + Vector((0, 0.065, 0)), scale=(0.018, 0.018, 0.018))
        ob = mb.build(name + "_Sword", COLL)
        rig_rigid(ob, 'hand.R')
        out.append(ob)
        # 背中の鞘（フィールド用）
        mb = CMB()
        sheath = mat("Sheath", (0.18, 0.2, 0.45), 0.5)
        a, b = Vector((-0.12, 0.13, 1.42)), Vector((0.16, 0.15, 0.78))
        mb.tube([a + (b - a) * u for u in (0, 0.5, 1.0)], [0.026, 0.024, 0.016], sheath, seg=12, flat=0.45)
        mb.add('cube', gold, loc=a + (b - a) * 0.02, rot=(0, -0.42, 0), scale=(0.15, 0.02, 0.025))
        mb.add('cyl', leather, loc=a - (b - a).normalized() * 0.06, rot=(0, -0.42 + math.pi, 0), r1=0.013, r2=0.013, depth=0.1, seg=10)
        mb.add('sphere', mat("Sapphire", (0.15, 0.35, 1.0), 0.1), loc=a - (b - a).normalized() * 0.115, scale=(0.017, 0.017, 0.017))
        ob = mb.build(name + "_Sheath", COLL)
        rig_rigid(ob, 'chest')
        out.append(ob)
    if cfg.get('axe'):
        mb = CMB()
        iron = mat("AxeIron", (0.42, 0.44, 0.48), 0.42, 1.0)
        edge = mat("Blade", (0.92, 0.94, 0.98), 0.12, 1.0, double=True)
        mb.add('cyl', wood, loc=hpalm + Vector((0, 0, 0.12)), r1=0.021, r2=0.019, depth=1.05, seg=12)
        top = hpalm + Vector((0, 0, 0.55))
        for sd in (-1, 1):
            axe_head(mb, top, iron, edge, sd, wood)
        # 刃を留める金具（輪・びょう）と頭の突起
        mb.add('cyl', iron, loc=top, r1=0.034, r2=0.034, depth=0.3, seg=12)
        for dz in (-0.15, 0.15):
            mb.add('cyl', gold, loc=top + Vector((0, 0, dz)), r1=0.038, r2=0.038, depth=0.022, seg=16)
        for dz in (-0.07, 0.0, 0.07):
            for sx in (-1, 1):
                mb.add('sphere', gold, loc=top + Vector((sx * 0.017, 0, dz)), scale=(0.007, 0.007, 0.007), seg=8, rings=5)
        mb.add('cyl', iron, loc=top + Vector((0, 0, 0.24)), r1=0.022, r2=0.0, depth=0.16, seg=8)
        # 握りの革巻きと、石突き
        grip_wrap(mb, hpalm + Vector((0, 0, -0.16)), Vector((0, 0, 1)), 0.022, 0.32, leather, turns=9)
        mb.add('cyl', gold, loc=hpalm + Vector((0, 0, -0.41)), r1=0.026, r2=0.016, depth=0.06, seg=12)
        held(mb)
        ob = mb.build(name + "_Axe", COLL)
        rig_rigid(ob, 'hand.R')
        out.append(ob)
    if cfg.get('spear'):
        mb = CMB()
        mb.add('cyl', wood, loc=hpalm + Vector((0, 0, 0.35)), r1=0.014, r2=0.013, depth=2.0, seg=10)
        base = hpalm + Vector((0, 0, 1.33))
        # 木の葉形の穂先（中央に稜線のあるひし形の断面）
        secs = []
        for k in range(13):
            u = k / 12
            w = 0.034 * math.sin(math.pi * min(u * 1.25, 1.0)) ** 0.8 * (1 - u) ** 0.4 + 0.002
            t = 0.009 * (1 - u) + 0.0015
            z = 0.02 + u * 0.26
            secs.append([base + Vector((0, -w, z)), base + Vector((t, 0, z)), base + Vector((0, w, z)), base + Vector((-t, 0, z))])
        loft(mb, secs, mat("Blade", (0.92, 0.94, 0.98), 0.12, 1.0, double=True))
        mb.add('cyl', silver, loc=base + Vector((0, 0, -0.03)), r1=0.016, r2=0.012, depth=0.12, seg=10)
        mb.add('cyl', gold, loc=base + Vector((0, 0, -0.09)), r1=0.019, r2=0.019, depth=0.02, seg=12)
        # 赤い房
        tas = mat("Tassel", (0.75, 0.08, 0.1), 0.85)
        for k in range(10):
            a = k / 10 * math.tau
            p0 = base + Vector((math.cos(a) * 0.012, math.sin(a) * 0.012, -0.1))
            mb.tube([p0, p0 + Vector((math.cos(a) * 0.02, math.sin(a) * 0.02, -0.06)), p0 + Vector((math.cos(a) * 0.026, math.sin(a) * 0.026, -0.13))],
                    [0.006, 0.005, 0.002], tas, seg=6)
        mb.add('cyl', silver, loc=hpalm + Vector((0, 0, -0.66)), r1=0.016, r2=0.006, depth=0.06, seg=10)
        held(mb)
        ob = mb.build(name + "_Spear", COLL)
        rig_rigid(ob, 'hand.R')
        out.append(ob)
    if cfg.get('staff'):
        mb = CMB()
        kind = cfg['staff']
        top = hpalm + Vector((0, 0, 0.98))
        if kind == 'gold':
            mb.add('cyl', gold, loc=hpalm + Vector((0, 0, 0.25)), r1=0.012, r2=0.015, depth=1.45, seg=12)
            for dz in (-0.5, -0.1, 0.55):
                mb.add('cyl', gold, loc=hpalm + Vector((0, 0, dz)), r1=0.02, r2=0.02, depth=0.025, seg=14)
            # 輪の中に浮かぶ宝石と、左右の翼の飾り
            ring = [top + Vector((math.cos(k / 32 * math.tau) * 0.07, 0, 0.09 + math.sin(k / 32 * math.tau) * 0.08)) for k in range(33)]
            mb.tube(ring, [0.008] * 33, gold, seg=8)
            mb.add('sphere', mat("Ruby", (0.9, 0.05, 0.1), 0.1), loc=top + Vector((0, 0, 0.09)), scale=(0.032, 0.032, 0.042), seg=20, rings=12)
            mb.add('sphere', gold, loc=top, scale=(0.026, 0.026, 0.03))
            for sx in (-1, 1):
                for k in range(3):
                    a0 = top + Vector((sx * (0.06 + k * 0.012), 0, 0.05 - k * 0.012))
                    mb.tube([a0, a0 + Vector((sx * 0.05, 0, 0.05 - k * 0.02)), a0 + Vector((sx * 0.09, 0, 0.09 - k * 0.04))],
                            [0.008, 0.007, 0.002], gold, seg=6, flat=0.4)
            mb.add('cyl', gold, loc=hpalm + Vector((0, 0, -0.5)), r1=0.014, r2=0.004, depth=0.05, seg=10)
        else:
            # ねじれた木の杖：2 本の枝がからみ合い、上で宝石を包む
            for ph in (0.0, math.pi):
                pts = []
                for k in range(29):
                    t = k / 28
                    z = -0.47 + t * 1.42
                    a = ph + t * math.tau * 3.0
                    rr = 0.009 + 0.004 * t
                    pts.append(hpalm + Vector((math.cos(a) * rr, math.sin(a) * rr, z)))
                mb.tube(pts, [0.011 - 0.002 * (k / 28) for k in range(29)], wood, seg=8)
            for sx in (-1, 1):
                pts = [top + Vector((0, 0, -0.04)), top + Vector((sx * 0.045, 0, 0.0)), top + Vector((sx * 0.05, 0, 0.07)),
                       top + Vector((sx * 0.02, 0, 0.12)), top + Vector((-sx * 0.008, 0, 0.115))]
                mb.tube(pts, [0.011, 0.01, 0.008, 0.006, 0.003], wood, seg=8)
            mb.add('ico', mat("MagicGlow", (0.75, 0.35, 1.0), 0.2, emit=(0.75, 0.30, 1.0), emit_strength=4.0),
                   loc=top + Vector((0, 0, 0.055)), r=0.034, sub=2)
            for k in range(4):
                a = k / 4 * math.tau + 0.4
                mb.add('ico', mat("MagicGlow", (0.75, 0.35, 1.0), 0.2, emit=(0.75, 0.30, 1.0), emit_strength=4.0),
                       loc=top + Vector((math.cos(a) * 0.012, math.sin(a) * 0.012, -0.08 - k * 0.012)), r=0.006, sub=1)
            grip_wrap(mb, hpalm + Vector((0, 0, -0.08)), Vector((0, 0, 1)), 0.016, 0.2, mat("Leather", (0.30, 0.18, 0.10), 0.6), turns=6)
        held(mb)
        ob = mb.build(name + "_Staff", COLL)
        rig_rigid(ob, 'hand.R')
        out.append(ob)
    # 左腕の盾
    if cfg.get('shield'):
        el, wr = Vector(BMAP['forearm.L'][1]), Vector(BMAP['forearm.L'][2])
        c = el.lerp(wr, 0.5) + Vector((0.055, 0, 0))
        d = (wr - el).normalized()
        mb = CMB()
        sh = mat(name + "_Shield", cfg['shield'], 0.4, 0.4)
        rot = Vector((0, 0, 1)).rotation_difference(Vector((1, 0, 0.35)).normalized()).to_euler()
        mb.add('sphere', sh, loc=c, rot=rot, scale=(0.2, 0.24, 0.035), seg=32, rings=16)
        mb.add('cyl', gold, loc=c, rot=rot, r1=0.205, r2=0.205, depth=0.02, seg=32, scale=(1, 1.2, 1))
        n = Vector((1, 0, 0.35)).normalized()
        mb.add('sphere', gold, loc=c + n * 0.035, rot=rot, scale=(0.05, 0.05, 0.015))
        mb.add('cube', gold, loc=c + n * 0.03, rot=rot, scale=(0.03, 0.34, 0.008))
        mb.add('cube', gold, loc=c + n * 0.03 + Vector((0, 0, 0.05)), rot=rot, scale=(0.26, 0.03, 0.008))
        # ふちのびょう
        R = rot.to_matrix()
        for k in range(16):
            a = k / 16 * math.tau
            q = c + R @ Vector((math.cos(a) * 0.19, math.sin(a) * 0.228, 0.012))
            mb.add('sphere', gold, loc=q, scale=(0.009, 0.009, 0.009), seg=8, rings=5)
        ob = mb.build(name + "_Shield", COLL)
        rig_rigid(ob, 'forearm.L')
        out.append(ob)
    return out


# ------------------------------------------------------------------ デザインの部品（スカーフ・ベルト・ふくらみ袖・リボン・毛皮・三つ編み・ツインテール）
def make_bow(mb, c, right, up, size, m, tails=True):
    """リボン結び：左右の輪＋結び目＋垂れ"""
    right, up = right.normalized(), up.normalized()
    fwd = right.cross(up).normalized()
    for sg in (-1, 1):
        pts = []
        for k in range(17):
            t = k / 16
            a = t * math.tau
            pts.append(c + right * sg * size * (0.12 + 0.9 * math.sin(t * math.pi) ** 0.8) + up * size * 0.42 * math.sin(a) * (0.6 + 0.4 * math.sin(t * math.pi)) - fwd * size * 0.08 * math.sin(t * math.pi))
        mb.tube(pts, [size * 0.16 * (0.5 + 0.5 * math.sin(k / 16 * math.pi)) + size * 0.03 for k in range(17)], m, seg=8, flat=0.4)
        if tails:
            mb.tube([c, c + right * sg * size * 0.35 - up * size * 0.6, c + right * sg * size * 0.55 - up * size * 1.25],
                    [size * 0.12, size * 0.11, size * 0.05], m, seg=8, flat=0.35)
    mb.add('sphere', m, loc=c, scale=(size * 0.2, size * 0.14, size * 0.2), seg=12, rings=8)


def build_scarf(cfg, surf):
    col = cfg.get('scarf')
    if not col:
        return []
    m = mat(cfg['name'] + "_Scarf", col, 0.8, double=True)
    mb = CMB()
    c0 = Vector((0, 0.004, 1.43))
    pts = []
    for k in range(49):
        ang = k / 48 * math.tau
        d = Vector((math.sin(ang), -math.cos(ang), 0.0))
        hit, nn = surf.ray(c0, d, 0.12)
        dist = (hit - c0).length if hit is not None else 0.06
        dist = min(dist, 0.06)
        front = max(0.0, math.cos(ang))
        pts.append(c0 + d * (dist + 0.022 + 0.004 * math.sin(ang * 7)) + Vector((0, 0, -0.012 * front + 0.004 * math.sin(ang * 5))))
    mb.tube(pts, [0.024] * len(pts), m, seg=12, flat=0.75)
    # 結び目と、背中へなびく 2 本の端
    knot = Vector((-0.045, 0.05, 1.43))
    mb.add('sphere', m, loc=knot, scale=(0.03, 0.028, 0.03))
    rows, cols = 12, 3
    for k, (dx, ln) in enumerate(((-0.02, 0.42), (0.025, 0.34))):
        verts, faces = [], []
        for r in range(rows + 1):
            v = r / rows
            w = 0.05 - 0.012 * v
            cx = knot.x + dx + 0.03 * math.sin(v * 2.5 + k)
            cy = knot.y + 0.03 + v * 0.12 + 0.015 * math.sin(v * 5 + k)
            cz = knot.z - v * ln
            for cc in range(cols + 1):
                u = cc / cols * 2 - 1
                verts.append((cx + u * w * 0.5, cy + 0.006 * math.sin(u * 3 + v * 6), cz))
        for r in range(rows):
            for cc in range(cols):
                a_ = r * (cols + 1) + cc
                faces.append((a_, a_ + 1, a_ + cols + 2, a_ + cols + 1))
        mb.poly(verts, faces, m, smooth=True)
    ob = mb.build(cfg['name'] + "_Scarf", COLL)

    def wf(v):
        z = v.co.z
        if v.co.y < 0.06 or z > 1.38:
            return weights_for(v.co, cfg)
        k = max(0.0, min(1.0, (1.38 - z) / 0.36))
        return {'chest': 1 - k, 'cape.1': k}
    assign_vgroups(ob, wf)
    return [ob]


def build_bandolier(cfg, surf):
    """肩から反対の腰へ斜めにかけた革ベルトとポーチ"""
    if not cfg.get('bandolier'):
        return []
    lm = cmat(cfg, 'belt')
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    mb = CMB()
    front, back = [], []
    for k in range(13):
        t = k / 12
        x = 0.12 - 0.25 * t
        z = 1.42 - 0.44 * t
        q, nn = surf.front(x, z)
        front.append(q + nn * 0.012)
        hit, nn2 = surf.ray(Vector((x, 0.6, z)), Vector((0, -1, 0)), 1.0)
        if hit is not None:
            back.append(hit + nn2 * 0.012)
    mb.tube(front, [0.017] * len(front), lm, seg=8, flat=0.3)
    if len(back) > 3:
        mb.tube(back, [0.017] * len(back), lm, seg=8, flat=0.3)
    # 肩の上をまたぐ部分
    mb.tube([front[0], Vector((0.125, 0.02, 1.455)), back[0] if back else front[0]], [0.017] * 3, lm, seg=8, flat=0.3)
    q, nn = surf.front(0.035, 1.25)
    mb.add('cube', gold, loc=q + nn * 0.016, rot=basis_euler(nn), scale=(0.03, 0.008, 0.026), bevel=0.003)
    # ポーチ（ふた・留め金）
    q, nn = surf.front(-0.135, 0.955)
    pc = q + nn * 0.03
    e = basis_euler(nn)
    mb.add('cube', lm, loc=pc, rot=e, scale=(0.07, 0.045, 0.06), bevel=0.008)
    mb.add('cube', lm, loc=pc + nn * 0.004 + Vector((0, 0, 0.022)), rot=e, scale=(0.074, 0.05, 0.026), bevel=0.006)
    mb.add('sphere', gold, loc=pc + nn * 0.026 + Vector((0, 0, 0.012)), scale=(0.006, 0.006, 0.006), seg=8, rings=5)
    ob = mb.build(cfg['name'] + "_Bandolier", COLL)
    assign_vgroups(ob, lambda v: weights_for(v.co, cfg))
    return [ob]


def build_puff_sleeves(cfg, surf):
    if not cfg.get('puff'):
        return []
    m = cmat(cfg, 'top')
    cuff = mat("Frill", (1.0, 0.97, 0.95), 0.8)
    mb = CMB()
    for sd in ('L', 'R'):
        ua = BMAP[f'upper_arm.{sd}']
        a, b = Vector(ua[1]), Vector(ua[2])
        ax = (b - a).normalized()
        u = ax.cross(Vector((0, 1, 0))).normalized()
        v = ax.cross(u).normalized()
        seg, rows = 28, 10
        verts, faces = [], []
        for r in range(rows + 1):
            t = -0.05 + 0.55 * r / rows
            c = a.lerp(b, t)
            base = 0.04 + 0.034 * math.sin(math.pi * r / rows) ** 0.8
            for k in range(seg):
                ang = k / seg * math.tau
                rr = base * (1 + 0.07 * math.sin(ang * 8) * math.sin(math.pi * r / rows))
                verts.append(tuple(c + (u * math.cos(ang) + v * math.sin(ang)) * rr))
        for r in range(rows):
            for k in range(seg):
                i0 = r * seg + k
                i1 = r * seg + (k + 1) % seg
                faces.append((i0, i1, i1 + seg, i0 + seg))
        mb.poly(verts, faces, m, smooth=True)
        edge = [Vector(verts[rows * seg + k]) for k in range(seg)] + [Vector(verts[rows * seg])]
        mb.tube(edge, [0.006] * len(edge), cuff, seg=8, flat=1.3)
    ob = mb.build(cfg['name'] + "_Puffs", COLL)
    assign_vgroups(ob, lambda v_: weights_for(v_.co, cfg))
    return [ob]


def build_chest_bow(cfg, surf):
    col = cfg.get('chest_bow')
    if not col:
        return []
    mb = CMB()
    q, nn = surf.front(0, cfg.get('bow_z', 1.37))
    make_bow(mb, q + nn * 0.03, Vector((1, 0, 0)), Vector((0, 0, 1)), 0.05, mat(cfg['name'] + "_Bow", col, 0.6))
    ob = mb.build(cfg['name'] + "_ChestBow", COLL)
    rig_rigid(ob, 'chest')
    return [ob]


def build_fur_mantle(cfg):
    """肩をおおう毛皮：芯の上に短い毛束を何重にも並べる"""
    col = cfg.get('fur_mantle')
    if not col:
        return []
    m = mat(cfg['name'] + "_Fur", col, 0.95)
    m2 = mat(cfg['name'] + "_FurDark", tuple(c * 0.7 for c in col), 0.95)
    rng = random.Random(3)
    mb = CMB()
    core = []
    for k in range(49):
        a = k / 48 * math.tau
        core.append(Vector((math.sin(a) * 0.18, 0.02 - math.cos(a) * 0.125, 1.405 + 0.02 * math.cos(a))))
    mb.tube(core, [0.035] * len(core), m2, seg=12, flat=0.7)
    for row, (rr, dz) in enumerate(((1.0, 0.03), (1.08, 0.0), (1.14, -0.03))):
        n = 44
        for k in range(n):
            a = (k + 0.5 * row) / n * math.tau
            out_ = Vector((math.sin(a), -math.cos(a) * 0.7, 0)).normalized()
            base = Vector((math.sin(a) * 0.18 * rr, 0.02 - math.cos(a) * 0.125 * rr, 1.405 + 0.02 * math.cos(a) + dz))
            L = rng.uniform(0.04, 0.065)
            d = (out_ * 0.6 + Vector((0, 0, -0.8))).normalized()
            pts = [base, base + d * L * 0.5 + Vector((0, 0, 0.004)), base + d * L + Vector((rng.uniform(-1, 1) * 0.008, 0, -0.004))]
            nrm = [out_] * 3
            lock_mesh(mb, pts, nrm, [0.018, 0.014, 0.003], 0.5, m if (k + row) % 3 else m2, seg=8)
    ob = mb.build(cfg['name'] + "_FurMantle", COLL)
    assign_vgroups(ob, lambda v: weights_for(v.co, cfg))
    return [ob]


# ------------------------------------------------------------------ 重ね着（ケープ・前掛け・広がる袖口・胴着）
def build_capelet(cfg, surf):
    """肩をおおう短いケープ（首から肩の下まで、すそが少し広がる）＋金のふち"""
    col = cfg.get('capelet')
    if not col:
        return []
    m = mat(cfg['name'] + "_Capelet", col, 0.8)
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    rows, seg = 9, 64
    verts, faces = [], []
    z0, z1 = 1.445, cfg.get('capelet_bottom', 1.255)
    ring_last = []
    for r in range(rows + 1):
        v = r / rows
        z = z0 + (z1 - z0) * v
        c = Vector((0, 0.006, z))
        ring = []
        for k in range(seg):
            a = k / seg * math.tau
            d = Vector((math.sin(a), -math.cos(a), 0))
            hit, nn = surf.ray(c, d, 0.35)
            dist = (hit - c).length if hit is not None else 0.2
            # 腕の付け根で急に広がらないよう、上の段より大きく外へは出さない
            if ring_last:
                dist = min(dist, ring_last[k] + 0.014)
            dist = min(dist, 0.19)
            ring.append(dist)
            flare = 0.012 + 0.03 * v ** 2
            verts.append(tuple(c + d * (dist + flare) + Vector((0, 0, 0.004 * math.sin(a * 9) * v))))
        ring_last = ring
    for r in range(rows):
        for k in range(seg):
            a = r * seg + k
            b = r * seg + (k + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    mb = CMB()
    mb.poly(verts, faces, m, smooth=True)
    inner = []
    for v in verts:
        q = Vector(v)
        d = Vector((q.x, q.y - 0.006, 0))
        inner.append(tuple(q - (d.normalized() * 0.005 if d.length > 1e-6 else Vector())))
    mb.poly(inner, [tuple(reversed(f)) for f in faces], mat(cfg['name'] + "_Lining", tuple(c_ * 0.55 for c_ in col), 0.9), smooth=True)
    bottom = [Vector(verts[rows * seg + k]) for k in range(seg)] + [Vector(verts[rows * seg])]
    mb.tube(bottom, [0.006] * len(bottom), gold, seg=8, flat=1.3)
    top = [Vector(verts[k]) for k in range(seg)] + [Vector(verts[0])]
    mb.tube(top, [0.006] * len(top), gold, seg=8, flat=1.3)
    # 胸元の留め金
    q, nn = surf.front(0, 1.40)
    mb.add('sphere', gold, loc=q + nn * 0.02, scale=(0.016, 0.008, 0.016))
    mb.add('sphere', mat("Sapphire", (0.15, 0.35, 1.0), 0.1), loc=q + nn * 0.027, scale=(0.009, 0.005, 0.009))
    ob = mb.build(cfg['name'] + "_Capelet", COLL)
    assign_vgroups(ob, lambda v: weights_for(v.co, cfg))
    return [ob]


def build_tabard(cfg, surf):
    """胸から垂れる前掛け（金のふち・紋章）。ローブの上に重ねる"""
    col = cfg.get('tabard')
    if not col:
        return []
    m = mat(cfg['name'] + "_Tabard", col, 0.8, double=True)
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    rows, cols = 16, 8
    verts, faces = [], []
    z_top, z_bot = 1.3, 0.42

    fat = 0.03 if cfg.get('build') == 'portly' else 0.0

    def robe_r(z):
        prof = [(0.995, 0.150), (0.93, 0.168), (0.78, 0.192), (0.55, 0.225), (0.30, 0.255)]
        prof = [(zz, rr + fat * (1 - (0.995 - zz))) for zz, rr in prof]
        if z >= prof[0][0]:
            return None
        for (za, ra), (zb, rb) in zip(prof, prof[1:]):
            if zb <= z <= za:
                t = (za - z) / (za - zb)
                return ra + (rb - ra) * t
        return prof[-1][1]
    grid = []
    for r in range(rows + 1):
        v = r / rows
        z = z_top + (z_bot - z_top) * v
        w = 0.06 + 0.05 * v
        row = []
        for c in range(cols + 1):
            u = c / cols * 2 - 1
            x = u * w
            rr = robe_r(z)
            if rr is None:
                q, nn = surf.front(x, z)
                y = q.y - 0.012
            else:
                y = 0.012 - math.sqrt(max(rr * rr - x * x, 0.0)) * 0.9 - 0.022
            y -= 0.006 * math.sin(u * math.pi * 2) * v
            row.append(len(verts))
            verts.append((x, y, z))
        grid.append(row)
    for r in range(rows):
        for c in range(cols):
            faces.append((grid[r][c], grid[r + 1][c], grid[r + 1][c + 1], grid[r][c + 1]))
    mb = CMB()
    mb.poly(verts, faces, m, smooth=True)
    V_ = lambda i: Vector(verts[i]) + Vector((0, -0.004, 0))
    for c in (0, cols):
        mb.tube([V_(grid[r][c]) for r in range(rows + 1)], [0.0055] * (rows + 1), gold, seg=8, flat=1.2)
    mb.tube([V_(grid[rows][c]) for c in range(cols + 1)], [0.0055] * (cols + 1), gold, seg=8, flat=1.2)
    # 紋章（金の輪と十字）
    ec = Vector(verts[grid[5][cols // 2]]) + Vector((0, -0.006, 0))
    ring = [ec + Vector((math.cos(k / 24 * math.tau) * 0.035, 0, math.sin(k / 24 * math.tau) * 0.035)) for k in range(25)]
    mb.tube(ring, [0.004] * 25, gold, seg=6)
    mb.add('cube', gold, loc=ec, scale=(0.008, 0.006, 0.06))
    mb.add('cube', gold, loc=ec + Vector((0, 0, 0.008)), scale=(0.045, 0.006, 0.008))
    ob = mb.build(cfg['name'] + "_TabardCloth", COLL)
    zt = 0.975

    def wf(v):
        z = v.co.z
        if z > 1.0:
            return weights_for(v.co, cfg)
        u = max(0.0, min(1.0, (zt - z) / (zt - z_bot)))
        wl = 0.45 * u
        return {'hips': 1 - wl, 'thigh.L': wl / 2, 'thigh.R': wl / 2}
    assign_vgroups(ob, wf)
    return [ob]


def build_bell_cuffs(cfg, surf):
    """手首へ広がる袖口（神官服）＋金のふち"""
    if not cfg.get('bell_cuffs'):
        return []
    m = cmat(cfg, 'top')
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    mb = CMB()
    for sd in ('L', 'R'):
        fa = BMAP[f'forearm.{sd}']
        a, b = Vector(fa[1]), Vector(fa[2])
        ax = (b - a).normalized()
        u = ax.cross(Vector((0, 1, 0))).normalized()
        v = ax.cross(u).normalized()
        seg, rows = 24, 6
        verts, faces = [], []
        for r in range(rows + 1):
            t = 0.45 + 0.6 * r / rows
            c = a.lerp(b, t)
            rad = 0.04 + 0.04 * (r / rows) ** 1.6
            for k in range(seg):
                ang = k / seg * math.tau
                d = u * math.cos(ang) + v * math.sin(ang)
                verts.append(tuple(c + d * rad + Vector((0, 0, -0.012 * (r / rows) ** 2 * (1 + math.cos(ang - math.pi / 2))))))
        for r in range(rows):
            for k in range(seg):
                i0 = r * seg + k
                i1 = r * seg + (k + 1) % seg
                faces.append((i0, i1, i1 + seg, i0 + seg))
        mb.poly(verts, faces, m, smooth=True)
        mb.poly(verts, [tuple(reversed(f)) for f in faces], mat(cfg['name'] + "_Lining", tuple(c_ * 0.55 for c_ in cfg['colors'].get('top', (0.5, 0.5, 0.5))), 0.9), smooth=True)
        edge = [Vector(verts[rows * seg + k]) for k in range(seg)] + [Vector(verts[rows * seg])]
        mb.tube(edge, [0.0045] * len(edge), gold, seg=6)
    ob = mb.build(cfg['name'] + "_Sleeves", COLL)
    assign_vgroups(ob, lambda v_: weights_for(v_.co, cfg))
    return [ob]


def build_corset(cfg, surf):
    """胴を締める幅広の胴着ベルト（上下に金のふち）と襟の星のブローチ"""
    col = cfg.get('corset')
    if not col:
        return []
    m = mat(cfg['name'] + "_Corset", col, 0.6)
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    mb = CMB()
    rows, seg = 6, 56
    verts, faces = [], []
    for r in range(rows + 1):
        z = 1.13 - 0.15 * r / rows
        c = Vector((0, 0.006, z))
        for k in range(seg):
            a = k / seg * math.tau
            d = Vector((math.sin(a), -math.cos(a), 0))
            hit, nn = surf.ray(c, d, 0.3)
            dist = (hit - c).length if hit is not None else 0.12
            verts.append(tuple(c + d * (dist + 0.007)))
    for r in range(rows):
        for k in range(seg):
            i0 = r * seg + k
            i1 = r * seg + (k + 1) % seg
            faces.append((i0, i1, i1 + seg, i0 + seg))
    mb.poly(verts, faces, m, smooth=True)
    for r in (0, rows):
        ring = [Vector(verts[r * seg + k]) for k in range(seg)] + [Vector(verts[r * seg])]
        mb.tube(ring, [0.004] * len(ring), gold, seg=6)
    # 前の編み上げ
    pts = []
    for k in range(5):
        z = 1.12 - k * 0.03
        for sx in ((-1, 1) if k % 2 == 0 else (1, -1)):
            q, nn = surf.front(sx * 0.018, z)
            pts.append(q + nn * 0.011)
    mb.tube(pts, [0.0022] * len(pts), gold, seg=6)
    # 星のブローチ
    q, nn = surf.front(0, 1.415)
    if not cfg.get('brooch', True):
        ob = mb.build(cfg['name'] + "_Corset", COLL)
        assign_vgroups(ob, lambda v_: weights_for(v_.co, cfg))
        return [ob]
    star = []
    for k in range(11):
        a = k / 10 * math.tau
        rr = 0.02 if k % 2 == 0 else 0.009
        star.append(q + nn * 0.012 + Vector((math.sin(a) * rr, 0, math.cos(a) * rr)))
    mb.poly([tuple(q + nn * 0.016)] + [tuple(v) for v in star[:-1]], [(0, i + 1, (i + 1) % 10 + 1) for i in range(10)], gold)
    mb.add('sphere', mat("MagicGlow", (0.75, 0.35, 1.0), 0.2, emit=(0.75, 0.30, 1.0), emit_strength=4.0), loc=q + nn * 0.018, scale=(0.006, 0.004, 0.006))
    ob = mb.build(cfg['name'] + "_Corset", COLL)
    assign_vgroups(ob, lambda v_: weights_for(v_.co, cfg))
    return [ob]


def limb_loft(mb, surf, a, b, t0, t1, add, m, rows=6, seg=24, flare=0.0):
    """手足の表面から少し浮かせた筒（籠手など）。端は少し広がる"""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    u = ax.cross(Vector((0, 1, 0)))
    if u.length < 1e-3:
        u = ax.cross(Vector((1, 0, 0)))
    u.normalize()
    v = ax.cross(u).normalized()
    verts, faces, rings = [], [], []
    for r in range(rows + 1):
        t = t0 + (t1 - t0) * r / rows
        c = a.lerp(b, t)
        ring = []
        for k in range(seg):
            ang = k / seg * math.tau
            d = u * math.cos(ang) + v * math.sin(ang)
            hit, nn = surf.ray(c, d, 0.2)
            dist = (hit - c).length if hit is not None else 0.04
            ring.append(len(verts))
            verts.append(tuple(c + d * (dist + add + flare * (r / rows) ** 2)))
        rings.append(ring)
    for r in range(rows):
        for k in range(seg):
            i0, i1 = rings[r][k], rings[r][(k + 1) % seg]
            j0, j1 = rings[r + 1][k], rings[r + 1][(k + 1) % seg]
            faces.append((i0, j0, j1, i1))
    mb.poly(verts, faces, m, smooth=True)
    return [Vector(verts[i]) for i in rings[0]], [Vector(verts[i]) for i in rings[-1]]


def build_accessories(cfg, surf, body):
    """籠手・ブーツのベルト・肩当て・首飾り"""
    out = []
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    mb = CMB()
    any_ = False
    br = cfg.get('bracers')
    if br:
        bm_ = mat(cfg['name'] + "_Bracer", br, 0.35 if sum(br) > 1.5 else 0.6, 1.0 if sum(br) > 1.5 else 0.0)
        for sd in ('L', 'R'):
            fa = BMAP[f'forearm.{sd}']
            r0, r1 = limb_loft(mb, surf, fa[1], fa[2], 0.5, 0.86, 0.009, bm_, flare=0.004)
            mb.tube(r0 + [r0[0]], [0.0045] * (len(r0) + 1), gold, seg=6)
            mb.tube(r1 + [r1[0]], [0.0045] * (len(r1) + 1), gold, seg=6)
            a, b = Vector(fa[1]), Vector(fa[2])
            c = a.lerp(b, 0.68)
            for k in range(3):
                ang = k / 3 * math.tau + 0.4
                ax = (b - a).normalized()
                u = ax.cross(Vector((0, 1, 0))).normalized()
                v = ax.cross(u).normalized()
                d = u * math.cos(ang) + v * math.sin(ang)
                hit, nn = surf.ray(c, d, 0.2)
                if hit is not None:
                    mb.add('sphere', gold, loc=hit + d * 0.011, scale=(0.0055, 0.0055, 0.0055), seg=8, rings=5)
        any_ = True
    if cfg.get('boot_straps'):
        sm = cmat(cfg, 'belt')
        for sd in ('L', 'R'):
            sh = BMAP[f'shin.{sd}']
            a, b = Vector(sh[1]), Vector(sh[2])
            bh = cfg.get('boot_h', 0.33)
            for z in (bh - 0.07, bh - 0.17):
                t = (a.z - z) / (a.z - b.z)
                limb_ring(mb, surf, a, b, t, 0.006, 0.006, sm, flat=0.45)
                q = a.lerp(b, t)
                hit, nn = surf.ray(q, Vector((0, -1, 0)), 0.2)
                if hit is not None:
                    mb.add('cube', gold, loc=hit + Vector((0, -0.011, 0)), scale=(0.018, 0.005, 0.014), bevel=0.002)
        any_ = True
    if cfg.get('pendant'):
        pts = []
        for k in range(17):
            t = k / 16
            ang = (t - 0.5) * 2.3
            x = math.sin(ang) * 0.075
            z = 1.425 - (1 - math.cos(ang)) * 0.0 - (math.cos(ang * 0.5)) * 0.06 + 0.06
            q, nn = surf.front(x, z)
            pts.append(q + nn * 0.006)
        mb.tube(pts, [0.0022] * len(pts), gold, seg=6)
        q, nn = surf.front(0, 1.355)
        mb.add('sphere', gold, loc=q + nn * 0.01, scale=(0.014, 0.006, 0.018))
        mb.add('sphere', mat("Sapphire", (0.15, 0.35, 1.0), 0.1), loc=q + nn * 0.015, scale=(0.009, 0.004, 0.012))
        any_ = True
    if any_:
        ob = mb.build(cfg['name'] + "_Accessories", COLL)
        assign_vgroups(ob, lambda v: weights_for(v.co, cfg))
        out.append(ob)
    sg = cfg.get('shoulder_guard')
    if sg:
        sgm = mat(cfg['name'] + "_ShoulderGuard", sg, 0.55)
        for k, (z0, z1, t) in enumerate(((1.355, 1.46, 0.022), (1.315, 1.395, 0.016))):
            out += build_shell(cfg, body, lambda c, z0=z0, z1=z1: (c.x > 0.1 and z0 < c.z < z1 and c.x < 0.26), t, sgm,
                               cfg['name'] + f"_Guard{k}", rim=gold, rim_r=0.004)
    return out


# ------------------------------------------------------------------ 武器の部品
def loft(mb, sections, m, cap=True, smooth=False):
    """同じ点数の断面（Vector のリスト）を順につないだ立体"""
    verts, faces = [], []
    n = len(sections[0])
    for sec in sections:
        verts += [tuple(v) for v in sec]
    for i in range(len(sections) - 1):
        for k in range(n):
            a = i * n + k
            b = i * n + (k + 1) % n
            faces.append((a, b, b + n, a + n))
    if cap:
        faces.append(tuple(reversed(range(n))))
        last = (len(sections) - 1) * n
        faces.append(tuple(range(last, last + n)))
    mb.poly(verts, faces, m, smooth=smooth)


def grip_wrap(mb, base, axis, r, length, m, turns=7):
    """柄に巻いた革ひも（らせん）"""
    axis = axis.normalized()
    u = axis.cross(Vector((1, 0, 0)))
    if u.length < 1e-3:
        u = axis.cross(Vector((0, 1, 0)))
    u.normalize()
    v = axis.cross(u)
    pts = []
    n = turns * 12
    for k in range(n + 1):
        t = k / n
        a = t * turns * math.tau
        pts.append(base + axis * (t * length) + (u * math.cos(a) + v * math.sin(a)) * r)
    mb.tube(pts, [0.0045] * len(pts), m, seg=6)


def axe_head(mb, top, iron, edge_m, side_y, wood):
    """両刃の斧の片側：柄から刃先へ薄くなる。刃先の帯は明るい鋼"""
    secs_body, secs_edge = [], []
    zs = [-0.17 + k * 0.025 for k in range(16)]
    for z in zs:
        u = (z + 0.17) / 0.375
        ye = 0.12 + 0.17 * math.sin(math.pi * u) ** 0.6 + 0.05 * (abs(u - 0.5) * 2) ** 3
        flare = 0.05 * (abs(u - 0.5) * 2) ** 4
        y0, y1 = 0.03, ye - 0.035
        t0 = 0.028 * (1 - 0.35 * abs(u - 0.5) * 2)
        t1, te = 0.012, 0.003
        sb = [top + Vector((t0 / 2, side_y * y0, z)), top + Vector((t1 / 2, side_y * y1, z + flare)),
              top + Vector((-t1 / 2, side_y * y1, z + flare)), top + Vector((-t0 / 2, side_y * y0, z))]
        se = [top + Vector((t1 / 2, side_y * y1, z + flare)), top + Vector((te / 2, side_y * ye, z + flare * 1.3)),
              top + Vector((-te / 2, side_y * ye, z + flare * 1.3)), top + Vector((-t1 / 2, side_y * y1, z + flare))]
        secs_body.append(sb)
        secs_edge.append(se)
    loft(mb, secs_body, iron)
    loft(mb, secs_edge, edge_m)


# ------------------------------------------------------------------ アーマチュア
def make_armature(name):
    arm = bpy.data.armatures.new(name + "_Rig")
    arm.display_type = 'STICK'
    ob = bpy.data.objects.new(name, arm)
    COLL.objects.link(ob)
    vl = bpy.context.view_layer
    vl.objects.active = ob
    with bpy.context.temp_override(active_object=ob, object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.mode_set(mode='EDIT')
        for (bn, h, t, par, r) in BONES:
            eb = arm.edit_bones.new(bn)
            eb.head = h
            eb.tail = t
            eb.roll = 0.0
            if par:
                eb.parent = arm.edit_bones[par]
            eb.use_deform = True
        bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def attach(objs, arm_ob):
    for ob in objs:
        if ob is None:
            continue
        ob.parent = arm_ob
        mod = ob.modifiers.new("Armature", 'ARMATURE')
        mod.object = arm_ob


# ------------------------------------------------------------------ キャラクター生成
def build_character(cfg, x_offset):
    name = cfg['name']
    print("character", name)
    arm_ob = make_armature(name)
    me = meta_mesh(name + "_Body", body_elems(cfg), res=cfg.get('res', 0.0075))
    me = decimate(me, cfg.get('faces', 18000))
    cut_body(me, cfg)
    body = mesh_to_obj(me, name + "_Body")
    # 塗り分け
    keys = []
    for p in me.polygons:
        c = p.center
        bn, t = nearest_bone(c)
        k = paint(cfg, bn, t, c)
        if k not in keys:
            keys.append(k)
            me.materials.append(cmat(cfg, k))
        p.material_index = keys.index(k)
    region_of = {}
    for p in me.polygons:
        k = keys[p.material_index]
        if k in ('robe', 'dress'):
            for vi in p.vertices:
                region_of[vi] = k
    # ローブ・ドレスの下に隠れる脚は、すそと同じだけ動かす（走ると布を突き抜けないように）
    hem = 0.14 if cfg.get('robe') else (0.44 if cfg.get('dress') else None)
    if hem is not None:
        kind_ = 'robe' if cfg.get('robe') else 'dress'
        for v in me.vertices:
            if v.co.z > hem and v.co.z < 1.0 and abs(v.co.x) < 0.2:
                region_of.setdefault(v.index, kind_)
    assign_vgroups(body, lambda v: weights_for(v.co, cfg, region_of.get(v.index)))
    surf = Surface(me)
    parts = [body, build_cape(cfg), build_hands(cfg)] + build_face(cfg, surf) + build_beard(cfg, surf) + build_hair(cfg, surf) + build_robe(cfg)
    parts += build_tunic_skirt(cfg) + build_trims(cfg, surf)
    parts += build_capelet(cfg, surf) + build_tabard(cfg, surf) + build_bell_cuffs(cfg, surf) + build_corset(cfg, surf)
    parts += build_scarf(cfg, surf) + build_bandolier(cfg, surf) + build_puff_sleeves(cfg, surf) + build_chest_bow(cfg, surf) + build_fur_mantle(cfg)
    parts += build_accessories(cfg, surf, body)
    # 鎧・エプロン・ベスト
    if cfg.get('armor'):
        steel = mat("ArmorSilver", (0.72, 0.74, 0.78), 0.38, 1.0)
        trim = mat("ArmorTrim", (0.78, 0.6, 0.3), 0.35, 1.0)
        parts += build_shell(cfg, body, lambda c: 1.0 < c.z < 1.43 and abs(c.x) < 0.19, 0.012, steel, name + "_Armor", rim=trim, rim_r=0.0055)
        # 肩当ては 3 枚の板を重ねる
        for k, (z0, z1, t) in enumerate(((1.36, 1.44, 0.024), (1.32, 1.39, 0.018), (1.28, 1.35, 0.013))):
            parts += build_shell(cfg, body, lambda c, z0=z0, z1=z1: (abs(c.x) > 0.11 and z0 < c.z < z1 and abs(c.x) < 0.25), t, steel,
                                 name + f"_Pauldron{k}", rim=trim, rim_r=0.004)
        # 胸の中心の稜線と、びょう
        rmb = CMB()
        pts = []
        for k in range(9):
            z = 1.05 + k * 0.045
            q, nn = surf.front(0, z)
            pts.append(q + nn * 0.016)
        rmb.tube(pts, [0.006] * len(pts), steel, seg=8, flat=0.7)
        for z in (1.12, 1.24, 1.36):
            for sx in (-0.13, 0.13):
                q, nn = surf.front(sx, z)
                rmb.add('sphere', trim, loc=q + nn * 0.015, scale=(0.0065, 0.0065, 0.0065), seg=10, rings=6)
        rob = rmb.build(name + "_ArmorDetail", COLL)
        assign_vgroups(rob, lambda v: weights_for(v.co, cfg))
        parts.append(rob)
    if cfg.get('apron'):
        parts += build_shell(cfg, body, lambda c: c.y < -0.02 and 0.55 < c.z < 1.3 and abs(c.x) < 0.13, 0.01,
                             cmat(cfg, 'apron'), name + "_Apron", rim=cmat(cfg, 'apron'), rim_r=0.005)
    if cfg.get('vest'):
        parts += build_shell(cfg, body, lambda c: 0.98 < c.z < 1.40 and abs(c.x) < 0.17 and not (c.y < -0.05 and abs(c.x) < 0.03), 0.009,
                             cmat(cfg, 'vest'), name + "_Vest", rim=mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0), rim_r=0.004)
    parts += build_gear(cfg, surf)
    attach(parts, arm_ob)
    arm_ob.location = (x_offset, 0, 0)
    sc = cfg.get('scale', 1.0)
    arm_ob.scale = (sc, sc, sc)
    return arm_ob


SKIN_C = (1.0, 0.77, 0.63)
CHARS = [
    dict(name='Hero', bracers=(0.4, 0.26, 0.14), boot_straps=True, shoulder_guard=(0.36, 0.22, 0.12), build='male', eye_style='cool', tunic_flare=True, lacing=True, tunic_len=0.80, sleeves='long', gloves='fingerless',
         hair='spiky', headband=(0.82, 0.12, 0.1), scarf=(0.8, 0.13, 0.1), bandolier=True, sword=True, shield=(0.16, 0.3, 0.68),
         eye=(0.22, 0.32, 0.55), boot_h=0.36,
         colors=dict(skin=SKIN_C, top=(0.13, 0.26, 0.62), under=(0.95, 0.93, 0.88), pants=(0.32, 0.25, 0.2), boot=(0.36, 0.22, 0.12),
                     belt=(0.4, 0.24, 0.12), glove=(0.36, 0.22, 0.12), hair=(0.4, 0.24, 0.12))),
    dict(name='King', eyes='adult', tabard=(0.86, 0.68, 0.26), bell_cuffs=True, build='portly', robe=True, hem=True, sleeves='long', hair='short', beard='long', crown=True, fur=True,
         cape=(0.62, 0.06, 0.12), cape_len=0.12, staff='gold', eye=(0.25, 0.2, 0.15),
         colors=dict(skin=SKIN_C, top=(0.72, 0.12, 0.15), robe=(0.62, 0.08, 0.13), boot=(0.4, 0.25, 0.1), hair=(0.93, 0.93, 0.93),
                     beard=(0.95, 0.95, 0.95), sash=(1.0, 0.78, 0.25))),
    dict(name='Guard', eyes='adult', build='male', sleeves='long', gloves=True, hair='helmet', helmet=True, armor=True, spear=True, tunic_flare=True,
         tunic_len=0.78, eye=(0.2, 0.15, 0.1),
         colors=dict(skin=SKIN_C, top=(0.22, 0.28, 0.55), pants=(0.25, 0.25, 0.3), boot=(0.25, 0.18, 0.12), belt=(0.3, 0.2, 0.1),
                     glove=(0.35, 0.25, 0.15))),
    dict(name='Minister', eyes='adult', capelet=(0.16, 0.14, 0.32), tabard=(0.55, 0.42, 0.16), bell_cuffs=True, build='slim', robe=True, sleeves='long', hair='bald', beard='short', eye=(0.2, 0.2, 0.2),
         colors=dict(skin=SKIN_C, top=(0.26, 0.24, 0.52), robe=(0.24, 0.22, 0.48), boot=(0.3, 0.2, 0.1), hair=(0.6, 0.58, 0.55),
                     beard=(0.62, 0.6, 0.58))),
    dict(name='Villager', eyes='adult', lacing=True, vest=True, build='male', sleeves='long', hair='short', tunic_len=0.9, eye=(0.3, 0.2, 0.1),
         colors=dict(skin=SKIN_C, top=(0.42, 0.58, 0.28), pants=(0.45, 0.34, 0.24), boot=(0.35, 0.22, 0.12), belt=(0.3, 0.2, 0.1),
                     hair=(0.45, 0.28, 0.12), vest=(0.4, 0.28, 0.16))),
    dict(name='Girl', corset=(0.86, 0.42, 0.52), brooch=False, build='female', scale=0.94, dress=True, sleeves='short', hair='long', eye=(0.15, 0.45, 0.4),
         colors=dict(skin=SKIN_C, top=(1.0, 0.62, 0.68), dress=(0.98, 0.52, 0.62), pants=(0.97, 0.95, 0.92), boot=(0.55, 0.25, 0.2),
                     belt=(0.95, 0.9, 0.85), hair=(0.92, 0.6, 0.22), ribbon=(1.0, 0.95, 0.95))),
    dict(name='Innkeeper', eyes='adult', build='portly', sleeves='long', hair='short', beard='short', apron=True, tunic_len=0.9, eye=(0.2, 0.15, 0.1),
         colors=dict(skin=SKIN_C, top=(0.72, 0.56, 0.36), pants=(0.36, 0.3, 0.25), boot=(0.3, 0.2, 0.12), belt=(0.3, 0.2, 0.1),
                     hair=(0.24, 0.15, 0.1), beard=(0.26, 0.16, 0.1), apron=(0.96, 0.95, 0.9))),
    dict(name='Merchant', eyes='adult', build='male', sleeves='long', hair='turban', vest=True, tunic_len=0.9, eye=(0.15, 0.12, 0.1),
         colors=dict(skin=(0.92, 0.70, 0.55), top=(0.95, 0.88, 0.7), pants=(0.45, 0.25, 0.25), boot=(0.4, 0.22, 0.12),
                     belt=(0.7, 0.15, 0.15), hair=(0.15, 0.12, 0.1), hat=(0.98, 0.95, 0.88), hatband=(0.3, 0.55, 0.8),
                     gem=(0.1, 0.8, 0.4), vest=(0.25, 0.45, 0.72))),
    dict(name='Elder', eyes='adult', capelet=(0.3, 0.22, 0.38), bell_cuffs=True, build='slim', robe=True, sleeves='long', hair='bald', beard='long', staff='magic', eye=(0.25, 0.25, 0.3),
         colors=dict(skin=(0.98, 0.80, 0.70), top=(0.48, 0.38, 0.55), robe=(0.44, 0.34, 0.52), boot=(0.3, 0.2, 0.1),
                     hair=(0.9, 0.9, 0.9), beard=(0.95, 0.95, 0.95))),
    # ---- 仲間
    dict(name='Milia', boot_straps=True, eye_style='cute', puff=True, chest_bow=(1.0, 0.42, 0.6), bow_z=1.36, capelet=(0.98, 0.97, 0.95), capelet_bottom=1.36,
         stockings=True, build='female', scale=0.92, head_scale=1.06, dress=True, sleeves='short', hair='twintails', staff='magic',
         witch_hat=(0.3, 0.16, 0.5), cape=(0.34, 0.18, 0.55), cape_len=0.66, eye=(0.15, 0.62, 0.4), boot_h=0.3,
         colors=dict(skin=SKIN_C, top=(0.52, 0.3, 0.78), dress=(0.46, 0.24, 0.7), pants=(0.96, 0.92, 0.86), boot=(0.34, 0.16, 0.36),
                     belt=(0.95, 0.75, 0.25), hair=(1.0, 0.5, 0.25), ribbon=(1.0, 0.42, 0.6), stock=(0.46, 0.24, 0.7), stock2=(0.98, 0.96, 0.95))),
    dict(name='Gald', bracers=(0.72, 0.74, 0.78), boot_straps=True, eyes='adult', eye_style='cool', scar=True, fur_mantle=(0.42, 0.3, 0.2), build='male', scale=1.12, head_scale=0.92,
         sleeves='long', gloves=True, hair='spiky', beard='short', armor=True, axe=True, cape=(0.5, 0.1, 0.08), tunic_flare=True, tunic_len=0.8,
         eye=(0.3, 0.22, 0.12),
         colors=dict(skin=(0.9, 0.68, 0.52), top=(0.32, 0.24, 0.2), pants=(0.26, 0.22, 0.2), boot=(0.24, 0.15, 0.09), belt=(0.25, 0.16, 0.08),
                     glove=(0.32, 0.21, 0.12), hair=(0.62, 0.2, 0.08), beard=(0.55, 0.18, 0.08))),
    dict(name='Serena', pendant=True, eye_style='cute', capelet=(0.96, 0.96, 0.99), tabard=(0.22, 0.4, 0.82), bell_cuffs=True, chest_bow=(0.25, 0.45, 0.9), bow_z=1.31,
         braids=True, flower=(1.0, 0.75, 0.82), build='female', scale=0.95, head_scale=1.04, robe=True, sleeves='long', hair='long', staff='gold',
         circlet=True, eye=(0.22, 0.42, 0.88),
         colors=dict(skin=(1.0, 0.84, 0.74), top=(0.95, 0.95, 0.98), robe=(0.92, 0.93, 0.99), boot=(0.85, 0.8, 0.7),
                     hair=(0.9, 0.9, 0.97), ribbon=(0.3, 0.5, 0.9), sash=(0.25, 0.45, 0.85))),
]

# 既存の人型を削除（再実行用）
for cfg in CHARS:
    for ob in list(bpy.data.objects):
        if ob.name == cfg['name'] or ob.name.startswith(cfg['name'] + "_"):
            bpy.data.objects.remove(ob)

RIGS = {}
for i, cfg in enumerate(CHARS):
    RIGS[cfg['name']] = build_character(cfg, -2.0 - i * 1.5)

# ------------------------------------------------------------------ アニメーション
def R(x=0.0, y=0.0, z=0.0):
    return Euler((x, y, z), 'XYZ').to_quaternion()


def ELB(side, b):
    """ひじを曲げる。前腕に直角な軸で回すので、深く曲げても前腕が外へ開かない"""
    h, t = Vector(BMAP[f'forearm.{side}'][1]), Vector(BMAP[f'forearm.{side}'][2])
    f0 = (t - h).normalized()
    ax = f0.cross(Vector((0, 1, 0))).normalized()
    return Quaternion(ax, -b)


BASE = {
    'upper_arm.L': R(y=0.3), 'upper_arm.R': R(y=-0.3),
    'forearm.L': ELB('L', 0.18), 'forearm.R': ELB('R', 0.18),
    'hand.L': R(y=0.1), 'hand.R': R(y=-0.1),
}


def compose(*poses):
    out = {}
    for p in poses:
        for k, q in p.items():
            out[k] = q @ out[k] if k in out else q.copy()
    return out


def key_pose(arm_ob, frame, pose, hip_dz=0.0):
    for pb in arm_ob.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        q = pose.get(pb.name, Quaternion())
        M = pb.bone.matrix_local.to_quaternion()
        pb.rotation_quaternion = M.inverted() @ q @ M
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        if pb.name == 'hips':
            pb.location = (0, hip_dz, 0)
            pb.keyframe_insert('location', frame=frame)


def new_action(arm_ob, name):
    act = bpy.data.actions.get(name)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm_ob.animation_data_create()
    arm_ob.animation_data.action = act
    return act


def make_actions(arm):
    # Idle (60f)
    new_action(arm, "Idle")
    for f in range(0, 61, 10):
        p = f / 60 * math.tau
        br = math.sin(p)
        # 右足に重心を乗せた立ち方（腰と胸を逆にひねる・左ひざを軽く曲げる）、腕は力を抜いて少し開く
        key_pose(arm, f, compose(BASE, {
            'hips': R(y=0.035, z=0.07),
            'spine': R(y=-0.015, z=-0.02),
            'chest': R(x=-0.03 * br + 0.02, y=-0.03, z=-0.06),
            'neck': R(x=0.02 * br, z=0.02),
            'head': R(z=0.05 * math.sin(p * 0.5) + 0.03, x=0.015 * br - 0.02, y=0.04),
            'thigh.L': R(x=-0.09, y=0.02, z=0.04), 'shin.L': R(x=0.18), 'foot.L': R(x=-0.09),
            'thigh.R': R(z=-0.02),
            'upper_arm.L': R(y=-0.03 * br + 0.07, x=0.05), 'upper_arm.R': R(y=0.03 * br - 0.05, x=0.03),
            'forearm.L': ELB('L', 0.16), 'forearm.R': ELB('R', 0.1),
            'hand.L': R(z=0.12, x=0.1), 'hand.R': R(z=-0.08),
            'cape.1': R(x=0.03 + 0.02 * br), 'cape.2': R(x=0.02 * br),
        }), hip_dz=-0.006 - 0.004 * (1 - br) * 0.5)

    def cyc(table, phi):
        """8 キーの周期テーブルを Catmull-Rom で補間（phi: 0..1）"""
        n = len(table)
        x = (phi % 1.0) * n
        i = int(x)
        t = x - i
        p0, p1, p2, p3 = table[(i - 1) % n], table[i % n], table[(i + 1) % n], table[(i + 2) % n]
        return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)

    def locomotion(name, n, C):
        """歩行・走行：接地 → 沈み込み → パッシング → 蹴り出し の 8 キーポーズ。
        足首はかかと着地からつま先離地まで地面に沿うよう、太もも＋すねの角度を打ち消して決める"""
        new_action(arm, name)
        keys = 16
        for i in range(keys + 1):
            f = round(i / keys * n)
            phi = i / keys
            pose = dict(BASE)
            legs = {}
            for side, off in (('L', 0.0), ('R', 0.5)):
                ph = phi + off
                th = cyc(C['thigh'], ph)
                sh = cyc(C['shin'], ph)
                fa = cyc(C['foot'], ph)
                legs[side] = (th, sh, fa - (th + sh))
            c = math.cos(phi * math.tau)
            sn = math.sin(phi * math.tau)
            ca = math.cos((phi - C['lag']) * math.tau)
            anim = {
                'thigh.L': R(x=legs['L'][0]), 'shin.L': R(x=legs['L'][1]), 'foot.L': R(x=legs['L'][2]),
                'thigh.R': R(x=legs['R'][0]), 'shin.R': R(x=legs['R'][1]), 'foot.R': R(x=legs['R'][2]),
                'hips': R(z=-C['yaw'] * c, y=-C['roll'] * sn),
                'spine': R(x=C['lean'] * 0.5, z=C['yaw'] * 0.5 * c),
                'chest': R(x=C['lean'] * 0.5, z=C['yaw'] * 0.9 * c, y=C['roll'] * 0.6 * sn),
                'neck': R(z=-C['yaw'] * 0.3 * c),
                'head': R(x=-C['lean'] * 0.7, z=-C['yaw'] * 0.1 * c),
                'upper_arm.L': R(x=C['arm'] * ca), 'upper_arm.R': R(x=-C['arm'] * ca),
                'forearm.L': ELB('L', C['elbow'] + C['elbow2'] * max(0.0, -ca)), 'forearm.R': ELB('R', C['elbow'] + C['elbow2'] * max(0.0, ca)),
                'cape.1': R(x=C['cape'] + 0.05 * math.sin(2 * phi * math.tau)),
                'cape.2': R(x=C['cape'] * 0.5 + 0.08 * math.sin(2 * phi * math.tau + 1)),
            }
            for k_, q in anim.items():
                pose[k_] = q @ pose[k_] if k_ in pose else q
            key_pose(arm, f, pose, hip_dz=cyc(C['bob'], phi * 2))

    locomotion("Walk", 32, dict(
        thigh=[-0.42, -0.30, -0.02, 0.22, 0.38, 0.15, -0.25, -0.45],
        shin=[0.06, 0.28, 0.08, 0.12, 0.35, 1.05, 0.85, 0.30],
        foot=[-0.32, 0.0, 0.0, 0.12, 0.55, 0.35, 0.10, -0.15],
        bob=[-0.018, -0.034, -0.012, 0.012, 0.008, -0.004, -0.01, -0.016],
        yaw=0.09, roll=0.045, lean=0.05, arm=0.32, elbow=0.2, elbow2=0.3, lag=0.05, cape=0.18))
    locomotion("Run", 20, dict(
        thigh=[-0.78, -0.45, 0.05, 0.55, 0.65, 0.2, -0.55, -0.88],
        shin=[0.25, 0.6, 0.35, 0.35, 1.1, 1.9, 1.6, 0.7],
        foot=[-0.15, 0.05, 0.15, 0.6, 0.9, 0.5, 0.2, -0.05],
        bob=[-0.035, -0.065, -0.02, 0.03, 0.045, 0.03, 0.0, -0.02],
        yaw=0.13, roll=0.035, lean=0.32, arm=0.85, elbow=1.15, elbow2=0.35, lag=0.04, cape=0.75))

    # Attack（剣を振り下ろす 26f）
    new_action(arm, "Attack")
    ready = compose(BASE, {'cape.1': R(x=0.05)})
    wind = compose(BASE, {
        'upper_arm.R': R(x=-2.6, y=0.3), 'forearm.R': R(x=-0.9), 'hand.R': R(x=0.4),
        'chest': R(z=0.35, x=-0.12), 'spine': R(z=0.15), 'head': R(z=-0.3),
        'thigh.L': R(x=-0.25), 'thigh.R': R(x=0.2), 'shin.R': R(x=0.25), 'upper_arm.L': R(x=0.4),
        'cape.1': R(x=0.25),
    })
    strike = compose(BASE, {
        'upper_arm.R': R(x=-0.55, y=0.15), 'forearm.R': R(x=-0.15), 'hand.R': R(x=-0.3),
        'chest': R(z=-0.35, x=0.25), 'spine': R(x=0.15, z=-0.15), 'head': R(x=-0.15, z=0.25),
        'thigh.R': R(x=-0.75), 'shin.R': R(x=0.45), 'thigh.L': R(x=0.45), 'shin.L': R(x=0.35),
        'upper_arm.L': R(x=0.6), 'cape.1': R(x=0.55), 'cape.2': R(x=0.3),
    })
    key_pose(arm, 0, ready)
    key_pose(arm, 8, wind, hip_dz=0.01)
    key_pose(arm, 12, strike, hip_dz=-0.06)
    key_pose(arm, 18, strike, hip_dz=-0.06)
    key_pose(arm, 26, ready)

    # Ride（竜の背にまたがる 40f）：ひざを曲げて鞍をはさみ、手綱を持つように腕を前へ
    new_action(arm, "Ride")
    for f_, br in ((0, 0.0), (20, 1.0), (40, 0.0)):
        ride = compose(BASE, {
            'thigh.L': R(x=-1.25, y=-0.42), 'thigh.R': R(x=-1.25, y=0.42),
            'shin.L': R(x=1.35), 'shin.R': R(x=1.35),
            'foot.L': R(x=-0.25), 'foot.R': R(x=-0.25),
            'spine': R(x=0.12 + 0.03 * br), 'chest': R(x=0.06), 'head': R(x=-0.15 - 0.03 * br),
            'upper_arm.L': R(x=-0.55), 'upper_arm.R': R(x=-0.55),
            'forearm.L': ELB('L', 1.0), 'forearm.R': ELB('R', 1.0),
            'cape.1': R(x=0.55 + 0.1 * br), 'cape.2': R(x=0.35 + 0.08 * br),
        })
        key_pose(arm, f_, ride, hip_dz=-0.01 * br)

    # Cast（呪文 30f）
    new_action(arm, "Cast")
    cast = compose(BASE, {
        'upper_arm.L': R(x=-1.35, y=-0.5), 'upper_arm.R': R(x=-1.35, y=0.5), 'forearm.L': R(x=-0.25), 'forearm.R': R(x=-0.25),
        'hand.L': R(x=-0.5), 'hand.R': R(x=-0.5), 'chest': R(x=-0.12), 'head': R(x=-0.12), 'cape.1': R(x=0.3), 'cape.2': R(x=0.15),
        'thigh.L': R(x=-0.15), 'thigh.R': R(x=0.12),
    })
    key_pose(arm, 0, BASE)
    key_pose(arm, 9, cast, hip_dz=0.005)
    key_pose(arm, 22, cast, hip_dz=0.005)
    key_pose(arm, 30, BASE)

    # Hurt（16f）
    new_action(arm, "Hurt")
    hurt = compose(BASE, {
        'spine': R(x=-0.3), 'chest': R(x=-0.2), 'head': R(x=-0.35), 'upper_arm.L': R(x=0.5, y=-0.3), 'upper_arm.R': R(x=0.5, y=0.3),
        'thigh.L': R(x=0.2), 'thigh.R': R(x=-0.1), 'shin.L': R(x=0.3), 'cape.1': R(x=-0.2),
    })
    key_pose(arm, 0, BASE)
    key_pose(arm, 3, hurt, hip_dz=-0.03)
    key_pose(arm, 16, BASE)

    # Victory（剣を掲げる 40f）
    new_action(arm, "Victory")
    vic = compose(BASE, {
        'upper_arm.R': R(x=-2.85, y=0.35), 'forearm.R': R(x=-0.15), 'hand.R': R(x=1.25),
        'upper_arm.L': R(y=-0.25, x=0.3), 'forearm.L': R(x=-1.4, z=0.4), 'chest': R(x=-0.12), 'head': R(x=-0.25),
        'thigh.L': R(x=-0.1, y=0.08), 'thigh.R': R(x=0.05, y=-0.08), 'cape.1': R(x=0.35), 'cape.2': R(x=0.2),
    })
    key_pose(arm, 0, BASE)
    key_pose(arm, 12, vic, hip_dz=0.01)
    key_pose(arm, 40, vic, hip_dz=0.01)

    # Down（倒れる 30f）
    new_action(arm, "Down")
    down = compose(BASE, {
        'thigh.L': R(x=-1.55), 'thigh.R': R(x=-0.6), 'shin.L': R(x=2.2), 'shin.R': R(x=2.0), 'foot.L': R(x=-0.5),
        'spine': R(x=0.55), 'chest': R(x=0.3), 'head': R(x=0.4), 'upper_arm.L': R(x=-0.6), 'upper_arm.R': R(x=-0.6),
        'cape.1': R(x=0.5),
    })
    key_pose(arm, 0, BASE)
    key_pose(arm, 14, down, hip_dz=-0.42)
    key_pose(arm, 30, down, hip_dz=-0.42)

    # Talk（話すときの身振り 40f）
    new_action(arm, "Talk")
    for f in range(0, 41, 10):
        p = f / 40 * math.tau
        key_pose(arm, f, compose(BASE, {
            'upper_arm.R': R(x=-0.45 - 0.15 * math.sin(p), y=0.25), 'forearm.R': R(x=-0.9), 'hand.R': R(x=-0.2 * math.sin(p * 2)),
            'head': R(x=0.06 * math.sin(p * 2), z=0.05 * math.sin(p)), 'chest': R(x=-0.02),
        }))

    # すべてのアクションを NLA トラックに積む（glTF に全クリップを書き出すため）
    ad = arm.animation_data
    ad.action = None
    for nm in ("Idle", "Walk", "Run", "Attack", "Cast", "Hurt", "Victory", "Down", "Talk", "Ride"):
        act = bpy.data.actions[nm]
        tr = ad.nla_tracks.new()
        tr.name = nm
        st = tr.strips.new(nm, 0, act)
        try:
            if act.slots:
                st.action_slot = act.slots[0]
        except AttributeError:
            pass


make_actions(RIGS['Hero'])

if _temp_link:
    SCENE.collection.children.unlink(COLL)
print("characters done")
