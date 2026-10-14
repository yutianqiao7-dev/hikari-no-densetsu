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
    hs = cfg.get('head_scale', 1.12)
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
        el.append(E_ell((0, -0.03, 1.29), 0.12, 0.06, 0.07))
    if b == 'portly':
        el.append(E_ell((0, -0.035, 1.08), 0.17, 0.15, 0.16))
    for s in (-1, 1):
        el.append(E_ell((s * 0.148 * sw, 0.008, 1.37), 0.062, 0.058, 0.055))
    el.append(E_cap((0, 0.008, 1.37), (0, -0.003, 1.52), 0.041 if not fem else 0.036))
    # 頭
    head = [
        E_ell((0, 0.010, 1.625), 0.094, 0.104, 0.108),
        E_ell((0, -0.026, 1.565), 0.061, 0.066, 0.056),
        E_ell((0, -0.062, 1.533), 0.03, 0.024, 0.022),
        E_ell((0, -0.096, 1.583), 0.0075, 0.011, 0.013),
    ]
    for s in (-1, 1):
        head.append(E_ell((s * 0.042, -0.06, 1.574), 0.024, 0.018, 0.022))
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
            # 手のひら・指（ミトン）・親指
            E_dir(wr + hd * 0.035, hd, 0.04, 0.029 * lw, 0.015),
            E_dir(wr + hd * 0.082, hd, 0.034, 0.027 * lw, 0.0125),
            E_cap(wr + hd * 0.02 + Vector((0, -0.022, 0)), wr + hd * 0.055 + Vector((-s * 0.006, -0.036, 0)), 0.0105),
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
    if cfg.get('tunic_flare'):
        el.append(E_ell((0, 0.004, 0.86), 0.17, 0.125, 0.07))
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
    sl = cfg.get('sleeves', 'long')
    for sd, sx in (('L', 1), ('R', -1)):
        ua, fa = BMAP[f'upper_arm.{sd}'], BMAP[f'forearm.{sd}']

        def near(seg):
            return lambda c, seg=seg: seg_closest(c, seg[1], seg[2])[0] < 0.085 and c.x * sx > 0.1
        if sl != 'long':
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
                'boot': (0.32, 0.2, 0.1)}
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
    hs = cfg.get('head_scale', 1.12)
    fem = cfg.get('build') == 'female'

    def P(x, z):
        q = HEAD_PIVOT + (Vector((x, 0, z)) - HEAD_PIVOT) * hs
        return q.x, q.z

    mb = CMB()
    white = mat("EyeWhite", (1.0, 1.0, 1.0), 0.25)
    iris = mat(cfg['name'] + "_Iris", cfg.get('eye', (0.25, 0.15, 0.08)), 0.15)
    pupil = mat("Pupil", (0.02, 0.02, 0.03), 0.1)
    lash = mat("Lash", (0.06, 0.04, 0.04), 0.6)
    brow = cmat(cfg, 'hair') if cfg['colors'].get('hair') else mat("Brow", (0.3, 0.3, 0.3))
    mouth = mat("Mouth", (0.55, 0.22, 0.22), 0.5)
    ew, eh = (0.019, 0.027) if fem else (0.018, 0.023)
    for s in (-1, 1):
        cx, cz = P(s * 0.039, 1.597)
        p, n = surf.front(cx, cz)
        n = (n + Vector((0, -1.4, 0))).normalized()
        e = basis_euler(n)
        mb.add('sphere', white, loc=p - n * 0.0035, rot=e, scale=(ew * hs, 0.006, eh * hs), seg=20, rings=12)
        mb.add('sphere', iris, loc=p - n * 0.0015 + Vector((-s * 0.002, 0, -0.002)), rot=e, scale=(ew * 0.72 * hs, 0.005, eh * 0.8 * hs), seg=20, rings=12)
        mb.add('sphere', pupil, loc=p - n * 0.0005 + Vector((-s * 0.002, 0, -0.002)), rot=e, scale=(ew * 0.34 * hs, 0.0045, eh * 0.4 * hs), seg=14, rings=8)
        mb.add('sphere', white, loc=p + n * 0.0012 + Vector((s * 0.004, 0, 0.007)), rot=e, scale=(0.0032, 0.0018, 0.004), seg=10, rings=6)
        # 上まつげ
        pts, rad = [], []
        for k in range(7):
            a = math.radians(170 - k * 23.3)
            lx = cx + math.cos(a) * ew * hs * 1.05
            lz = cz + math.sin(a) * eh * hs * 1.0
            q, nn = surf.front(lx, lz)
            pts.append(q + nn * 0.0012)
            rad.append(0.0028 if not fem else 0.0034)
        if fem:
            q, nn = surf.front(cx + s * ew * hs * 1.35, cz + eh * hs * 0.45)
            if s > 0:
                pts.append(q + nn * 0.002)
                rad.append(0.0015)
            else:
                pts.insert(0, q + nn * 0.002)
                rad.insert(0, 0.0015)
        mb.tube(pts, rad, lash, seg=6)
        # 眉
        pts = []
        for k in range(5):
            bx, bz = P(s * (0.017 + k * 0.012), 1.634 + math.sin(k / 4 * math.pi) * 0.006 - k * 0.001)
            q, nn = surf.front(bx, bz)
            pts.append(q + nn * 0.002)
        mb.tube(pts, [0.0026, 0.0034, 0.0034, 0.003, 0.002], brow, seg=6, flat=0.55)
    # 口
    pts = []
    for k in range(5):
        u = (k - 2) / 2
        mx, mz = P(u * 0.013, 1.548 + abs(u) ** 2 * 0.0025)
        q, nn = surf.front(mx, mz)
        pts.append(q + nn * 0.0006)
    mb.tube(pts, [0.0014, 0.0022, 0.0024, 0.0022, 0.0014], mouth, seg=6, flat=0.6)
    ob = mb.build(cfg['name'] + "_Face", COLL)
    rig_rigid(ob, 'head')
    return ob


# ------------------------------------------------------------------ 髪
def build_hair(cfg, surf):
    """頭の形に沿って流れる平たい毛束を重ねて髪型を作る"""
    style = cfg.get('hair', 'short')
    if style in ('none', 'helmet'):
        return []
    hs = cfg.get('head_scale', 1.12)
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
        if style == 'long':
            elems += [E_ell((0, 0.07, 1.50), 0.1, 0.05, 0.14), E_ell((0, 0.074, 1.39), 0.094, 0.04, 0.09)]
        cap_m = hair_m
    me = meta_mesh(cfg['name'] + "_Hair", [head_xf(e, hs) for e in elems], res=0.006)
    me = decimate(me, 4000)
    cap = mesh_to_obj(me, cfg['name'] + "_Hair")
    cap.data.materials.append(cap_m)
    rig_hair(cap)
    out.append(cap)

    mb = CMB()

    def clump(th, ph0, ph1, width, ext=0.0, lift=0.0, droop=0.0, flat=0.42, twist=0.0, tail_down=0.0, steps=7):
        pts, rad = [], []
        for i in range(steps):
            u = i / (steps - 1)
            ph = ph0 + (ph1 - ph0) * u
            t = th + twist * u
            p = S(t, ph, 1.0 + 0.02 * math.sin(u * math.pi))
            pts.append(p)
        n_end = outward(th + twist, ph1)
        last = pts[-1]
        tang = (pts[-1] - pts[-2]).normalized()
        for j in range(1, 4):
            v = j / 3
            q = last + (tang * (1 - lift) + n_end * lift).normalized() * ext * v + Vector((0, 0, -droop * v * v - tail_down * v))
            pts.append(q)
        n = len(pts)
        for i in range(n):
            u = i / (n - 1)
            rad.append(width * (0.55 + 0.9 * math.sin(min(u * 1.6, 1.0) * math.pi * 0.5)) * (1 - u) ** 0.9 + 0.0012)
        mb.tube([P(q) for q in pts], [r * hs for r in rad], hair_m, seg=10, flat=flat)

    if style in ('spiky', 'short', 'long'):
        # 前髪
        nb = 9 if style != 'short' else 7
        for i in range(nb):
            u = i / (nb - 1) * 2 - 1
            th = u * math.radians(48)
            end = 1.42 + (0.06 if abs(u) < 0.3 else 0.0) - abs(u) * 0.05 + rng.uniform(-0.03, 0.03)
            clump(th, 0.12, end, 0.026 if style == 'spiky' else 0.022, ext=0.03 if style != 'short' else 0.015,
                  lift=0.15, droop=0.006, twist=-u * 0.25 + rng.uniform(-0.08, 0.08))
        # 横・後ろ
        ring = 22
        for i in range(ring):
            th = math.radians(55 + i / (ring - 1) * 250) + rng.uniform(-0.05, 0.05)
            back = -math.cos(th)  # 後ろほど 1
            if style == 'spiky':
                clump(th, 0.1, 1.75 + 0.35 * max(back, 0), 0.034, ext=0.05 + 0.04 * max(back, 0), lift=0.55,
                      droop=-0.01, twist=rng.uniform(-0.12, 0.12))
            elif style == 'short':
                clump(th, 0.1, 1.85 + 0.25 * max(back, 0), 0.03, ext=0.02, lift=0.1, droop=0.005)
            else:
                clump(th, 0.1, 2.0, 0.032, ext=0.12 + 0.12 * max(back, 0), lift=0.05, droop=0.02,
                      tail_down=0.08 + 0.1 * max(back, 0), twist=rng.uniform(-0.05, 0.05))
        # 頭頂のツンツン
        if style == 'spiky':
            for i in range(8):
                th = math.radians(rng.uniform(110, 250))
                clump(th, 0.05, rng.uniform(0.95, 1.3), 0.036, ext=rng.uniform(0.035, 0.06), lift=0.45, droop=0.0, flat=0.5)
            for s in (-1, 1):
                clump(s * math.radians(80), 0.6, 2.1, 0.022, ext=0.025, lift=-0.1, droop=0.012, flat=0.5)
        if style == 'long':
            for s in (-1, 1):
                clump(s * math.radians(60), 0.35, 1.9, 0.026, ext=0.16, lift=0.0, tail_down=0.06)
            rib = mat(cfg['name'] + "_Ribbon", cfg['colors'].get('ribbon', (1, 0.4, 0.55)), 0.5)
            for s in (-1, 1):
                mb.add('sphere', rib, loc=P((s * 0.05, 0.118, 1.69)), rot=(0, s * 0.5, 0), scale=(0.045 * hs, 0.012, 0.03 * hs))
            mb.add('sphere', rib, loc=P((0, 0.12, 1.69)), scale=(0.015, 0.015, 0.018))
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


def build_beard(cfg):
    kind = cfg.get('beard')
    if not kind:
        return []
    hs = cfg.get('head_scale', 1.12)
    el = [E_ell((0, -0.07, 1.528), 0.058, 0.04, 0.045)]
    for s in (-1, 1):
        el.append(E_ell((s * 0.062, -0.045, 1.56), 0.026, 0.04, 0.045))
    if kind == 'long':
        el += [E_ell((0, -0.08, 1.45), 0.052, 0.04, 0.085), E_ell((0, -0.075, 1.36), 0.032, 0.028, 0.05)]
    el = [head_xf(e, hs) for e in el]
    me = meta_mesh(cfg['name'] + "_Beard", el, res=0.007)
    me = decimate(me, 3000)
    ob = mesh_to_obj(me, cfg['name'] + "_Beard")
    bm_ = cmat(cfg, 'beard')
    ob.data.materials.append(bm_)
    mb = CMB()

    def P(p):
        return HEAD_PIVOT + (Vector(p) - HEAD_PIVOT) * hs
    for s in (-1, 1):
        mb.tube([P((0, -0.103, 1.567)), P((s * 0.022, -0.103, 1.562)), P((s * 0.042, -0.094, 1.552)), P((s * 0.058, -0.08, 1.535))],
                [0.011, 0.012, 0.009, 0.003], bm_, seg=10)
    ob2 = mb.build(cfg['name'] + "_Mustache", COLL)
    rig_hair(ob)
    rig_rigid(ob2, 'head')
    return [ob, ob2]


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


def build_shell(cfg, body_ob, region_fn, thickness, m, name, solid=0.006):
    """体の表面から一部を抜き出して服・鎧の層を作る（体にぴったり沿う）"""
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
    return ob


HOLD_BEND = 1.2   # 武器を持つ右ひじの曲げ（src/actors/actor.js と同じ値）


def build_gear(cfg, surf):
    name = cfg['name']
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    silver = mat("Silver", (0.85, 0.87, 0.92), 0.25, 1.0)
    wood = mat("Wood", (0.42, 0.27, 0.14), 0.8)
    leather = mat("Leather", (0.30, 0.18, 0.10), 0.6)
    hs = cfg.get('head_scale', 1.12)
    out = []

    def P(p):
        return HEAD_PIVOT + (Vector(p) - HEAD_PIVOT) * hs

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
            q = P((math.sin(a) * 0.118, 0.012 - math.cos(a) * 0.128, 1.662 + back * 0.03))
            pts.append(q)
        mb.tube(pts, [0.0075 * hs] * len(pts), bandm, seg=10, flat=1.5)
        knot = P((0, 0.142, 1.692))
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
        mb.add('cyl', hm, loc=P((0, 0.01, 1.715)), r1=0.215 * hs, r2=0.2 * hs, depth=0.018, seg=36)
        mb.tube([P((0, 0.01, 1.70)), P((0, 0.02, 1.83)), P((0, 0.05, 1.95)), P((0, 0.12, 2.05)), P((0, 0.2, 2.07))],
                [0.118 * hs, 0.088 * hs, 0.058 * hs, 0.025 * hs, 0.004], hm, seg=18)
        ring = [P((math.sin(k / 32 * math.tau) * 0.118, 0.01 - math.cos(k / 32 * math.tau) * 0.118, 1.735)) for k in range(33)]
        mb.tube(ring, [0.012 * hs] * 33, mat("HatBand", (0.95, 0.75, 0.25), 0.4, 0.6), seg=8, flat=1.6)
        mb.add('ico', mat("MagicGlow", (0.75, 0.35, 1.0), 0.2, emit=(0.75, 0.30, 1.0), emit_strength=4.0), loc=P((0.0, -0.11, 1.738)), r=0.022, sub=1)
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
        mb.add('sphere', silver, loc=P((0, 0.012, 1.655)), scale=(0.112 * hs, 0.122 * hs, 0.112 * hs), seg=32, rings=20)
        mb.add('cyl', silver, loc=P((0, 0.012, 1.6)), r1=0.12 * hs, r2=0.118 * hs, depth=0.02, seg=32)
        mb.add('cube', silver, loc=P((0, -0.118, 1.6)), scale=(0.012, 0.01, 0.07))
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
        mb.add('cube', gold, loc=palm + Vector((0, -0.065, 0)), scale=(0.17, 0.022, 0.03))
        for s in (-1, 1):
            mb.add('sphere', gold, loc=palm + Vector((s * 0.085, -0.065, 0)), scale=(0.018, 0.018, 0.018))
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
        iron = mat("AxeIron", (0.62, 0.64, 0.68), 0.3, 1.0)
        mb.add('cyl', wood, loc=hpalm + Vector((0, 0, 0.12)), r1=0.022, r2=0.02, depth=1.05, seg=10)
        top = hpalm + Vector((0, 0, 0.55))
        for sd in (-1, 1):
            # 三日月形の刃（前後に）
            pts = [(0, 0, 0.13), (0, sd * 0.16, 0.2), (0, sd * 0.27, 0.08), (0, sd * 0.29, -0.06), (0, sd * 0.22, -0.18), (0, 0, -0.1)]
            verts = [tuple(top + Vector(q)) for q in pts]
            verts += [tuple(top + Vector(q) + Vector((0.025, 0, 0))) for q in pts]
            n = len(pts)
            faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
            for k in range(n):
                faces.append((k, (k + 1) % n, n + (k + 1) % n, n + k))
            mb.poly([tuple(Vector(v) - Vector((0.0125, 0, 0))) for v in verts], faces, iron, smooth=False)
        mb.add('cube', gold, loc=top, scale=(0.06, 0.06, 0.12))
        mb.add('cyl', iron, loc=top + Vector((0, 0, 0.17)), r1=0.025, r2=0.0, depth=0.12, seg=6)
        held(mb)
        ob = mb.build(name + "_Axe", COLL)
        rig_rigid(ob, 'hand.R')
        out.append(ob)
    if cfg.get('spear'):
        mb = CMB()
        mb.add('cyl', wood, loc=hpalm + Vector((0, 0, 0.35)), r1=0.014, r2=0.013, depth=2.0, seg=10)
        mb.add('cyl', silver, loc=hpalm + Vector((0, 0, 1.43)), r1=0.035, r2=0.0, depth=0.18, seg=4, scale=(1, 0.3, 1))
        mb.add('cube', gold, loc=hpalm + Vector((0, 0, 1.33)), scale=(0.07, 0.02, 0.02))
        held(mb)
        ob = mb.build(name + "_Spear", COLL)
        rig_rigid(ob, 'hand.R')
        out.append(ob)
    if cfg.get('staff'):
        mb = CMB()
        kind = cfg['staff']
        mb.add('cyl', gold if kind == 'gold' else wood, loc=hpalm + Vector((0, 0, 0.25)), r1=0.013, r2=0.016, depth=1.45, seg=10)
        top = hpalm + Vector((0, 0, 0.98))
        if kind == 'gold':
            mb.add('sphere', gold, loc=top, scale=(0.04, 0.04, 0.04))
            mb.add('sphere', mat("Ruby", (0.9, 0.05, 0.1), 0.1), loc=top + Vector((0, 0, 0.05)), scale=(0.03, 0.03, 0.04))
        else:
            mb.tube([top + Vector((0, 0, -0.04)), top + Vector((0.05, 0, 0.04)), top + Vector((0.0, 0, 0.11)), top + Vector((-0.04, 0, 0.06))],
                    [0.016, 0.014, 0.012, 0.008], wood, seg=10)
            mb.add('ico', mat("MagicGlow", (0.75, 0.35, 1.0), 0.2, emit=(0.75, 0.30, 1.0), emit_strength=4.0),
                   loc=top + Vector((0, 0, 0.05)), r=0.032, sub=2)
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
        ob = mb.build(name + "_Shield", COLL)
        rig_rigid(ob, 'forearm.L')
        out.append(ob)
    return out


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
    assign_vgroups(body, lambda v: weights_for(v.co, cfg, region_of.get(v.index)))
    surf = Surface(me)
    parts = [body, build_face(cfg, surf), build_cape(cfg)] + build_beard(cfg) + build_hair(cfg, surf) + build_robe(cfg)
    # 鎧・エプロン・ベスト
    if cfg.get('armor'):
        parts.append(build_shell(cfg, body, lambda c: 1.0 < c.z < 1.43 and abs(c.x) < 0.19, 0.012,
                                 mat("ArmorSilver", (0.82, 0.84, 0.9), 0.3, 1.0), name + "_Armor"))
        parts.append(build_shell(cfg, body, lambda c: (abs(c.x) > 0.1 and 1.30 < c.z < 1.43 and abs(c.x) < 0.24), 0.02,
                                 mat("ArmorSilver", (0.82, 0.84, 0.9), 0.3, 1.0), name + "_Pauldrons"))
    if cfg.get('apron'):
        parts.append(build_shell(cfg, body, lambda c: c.y < -0.02 and 0.55 < c.z < 1.3 and abs(c.x) < 0.13, 0.01,
                                 cmat(cfg, 'apron'), name + "_Apron"))
    if cfg.get('vest'):
        parts.append(build_shell(cfg, body, lambda c: 0.98 < c.z < 1.40 and abs(c.x) < 0.17 and not (c.y < -0.05 and abs(c.x) < 0.03), 0.009,
                                 cmat(cfg, 'vest'), name + "_Vest"))
    parts += build_gear(cfg, surf)
    attach(parts, arm_ob)
    arm_ob.location = (x_offset, 0, 0)
    sc = cfg.get('scale', 1.0)
    arm_ob.scale = (sc, sc, sc)
    return arm_ob


SKIN_C = (1.0, 0.80, 0.68)
CHARS = [
    dict(name='Hero', build='male', tunic_flare=True, tunic_len=0.80, sleeves='short', gloves=True, hair='spiky',
         cape=(0.78, 0.13, 0.12), sword=True, shield=(0.18, 0.32, 0.72), eye=(0.30, 0.18, 0.10),
         colors=dict(skin=SKIN_C, top=(0.16, 0.38, 0.76), pants=(0.86, 0.82, 0.70), boot=(0.38, 0.23, 0.12),
                     belt=(0.32, 0.19, 0.10), glove=(0.42, 0.27, 0.14), hair=(0.24, 0.15, 0.09))),
    dict(name='King', build='portly', robe=True, hem=True, sleeves='long', hair='short', beard='long', crown=True, fur=True,
         cape=(0.62, 0.06, 0.12), cape_len=0.12, staff='gold', eye=(0.25, 0.2, 0.15),
         colors=dict(skin=SKIN_C, top=(0.72, 0.12, 0.15), robe=(0.62, 0.08, 0.13), boot=(0.4, 0.25, 0.1), hair=(0.93, 0.93, 0.93),
                     beard=(0.95, 0.95, 0.95), sash=(1.0, 0.78, 0.25))),
    dict(name='Guard', build='male', sleeves='long', gloves=True, hair='helmet', helmet=True, armor=True, spear=True, tunic_flare=True,
         tunic_len=0.78, eye=(0.2, 0.15, 0.1),
         colors=dict(skin=SKIN_C, top=(0.22, 0.28, 0.55), pants=(0.25, 0.25, 0.3), boot=(0.25, 0.18, 0.12), belt=(0.3, 0.2, 0.1),
                     glove=(0.35, 0.25, 0.15))),
    dict(name='Minister', build='slim', robe=True, sleeves='long', hair='bald', beard='short', eye=(0.2, 0.2, 0.2),
         colors=dict(skin=SKIN_C, top=(0.26, 0.24, 0.52), robe=(0.24, 0.22, 0.48), boot=(0.3, 0.2, 0.1), hair=(0.6, 0.58, 0.55),
                     beard=(0.62, 0.6, 0.58))),
    dict(name='Villager', build='male', sleeves='long', hair='short', tunic_len=0.9, eye=(0.3, 0.2, 0.1),
         colors=dict(skin=SKIN_C, top=(0.42, 0.58, 0.28), pants=(0.45, 0.34, 0.24), boot=(0.35, 0.22, 0.12), belt=(0.3, 0.2, 0.1),
                     hair=(0.45, 0.28, 0.12))),
    dict(name='Girl', build='female', scale=0.94, dress=True, sleeves='short', hair='long', eye=(0.15, 0.45, 0.4),
         colors=dict(skin=SKIN_C, top=(1.0, 0.62, 0.68), dress=(0.98, 0.52, 0.62), pants=(0.97, 0.95, 0.92), boot=(0.55, 0.25, 0.2),
                     belt=(0.95, 0.9, 0.85), hair=(0.92, 0.6, 0.22), ribbon=(1.0, 0.95, 0.95))),
    dict(name='Innkeeper', build='portly', sleeves='long', hair='short', beard='short', apron=True, tunic_len=0.9, eye=(0.2, 0.15, 0.1),
         colors=dict(skin=SKIN_C, top=(0.72, 0.56, 0.36), pants=(0.36, 0.3, 0.25), boot=(0.3, 0.2, 0.12), belt=(0.3, 0.2, 0.1),
                     hair=(0.24, 0.15, 0.1), beard=(0.26, 0.16, 0.1), apron=(0.96, 0.95, 0.9))),
    dict(name='Merchant', build='male', sleeves='long', hair='turban', vest=True, tunic_len=0.9, eye=(0.15, 0.12, 0.1),
         colors=dict(skin=(0.92, 0.70, 0.55), top=(0.95, 0.88, 0.7), pants=(0.45, 0.25, 0.25), boot=(0.4, 0.22, 0.12),
                     belt=(0.7, 0.15, 0.15), hair=(0.15, 0.12, 0.1), hat=(0.98, 0.95, 0.88), hatband=(0.3, 0.55, 0.8),
                     gem=(0.1, 0.8, 0.4), vest=(0.25, 0.45, 0.72))),
    dict(name='Elder', build='slim', robe=True, sleeves='long', hair='bald', beard='long', staff='magic', eye=(0.25, 0.25, 0.3),
         colors=dict(skin=(0.98, 0.80, 0.70), top=(0.48, 0.38, 0.55), robe=(0.44, 0.34, 0.52), boot=(0.3, 0.2, 0.1),
                     hair=(0.9, 0.9, 0.9), beard=(0.95, 0.95, 0.95))),
    # ---- 仲間
    dict(name='Milia', build='female', scale=0.93, head_scale=1.15, dress=True, sleeves='short', hair='long', staff='magic',
         witch_hat=(0.28, 0.14, 0.45), cape=(0.32, 0.18, 0.5), cape_len=0.62, eye=(0.2, 0.6, 0.35),
         colors=dict(skin=SKIN_C, top=(0.5, 0.3, 0.72), dress=(0.42, 0.22, 0.62), pants=(0.96, 0.92, 0.86), boot=(0.32, 0.18, 0.3),
                     belt=(0.95, 0.75, 0.25), hair=(0.98, 0.52, 0.28), ribbon=(0.95, 0.75, 0.25))),
    dict(name='Gald', build='male', scale=1.1, head_scale=1.05, sleeves='long', gloves=True, hair='short', beard='short', armor=True,
         axe=True, cape=(0.14, 0.32, 0.2), tunic_flare=True, tunic_len=0.8, eye=(0.25, 0.18, 0.1),
         colors=dict(skin=(0.92, 0.72, 0.58), top=(0.38, 0.3, 0.24), pants=(0.3, 0.26, 0.22), boot=(0.26, 0.17, 0.1), belt=(0.25, 0.16, 0.08),
                     glove=(0.35, 0.24, 0.14), hair=(0.55, 0.2, 0.08), beard=(0.5, 0.18, 0.08))),
    dict(name='Serena', build='female', scale=0.96, head_scale=1.13, robe=True, sleeves='long', hair='long', staff='gold', circlet=True,
         eye=(0.2, 0.35, 0.8),
         colors=dict(skin=(1.0, 0.84, 0.74), top=(0.94, 0.94, 0.97), robe=(0.9, 0.92, 0.98), boot=(0.85, 0.8, 0.7),
                     hair=(0.86, 0.88, 0.96), ribbon=(0.3, 0.5, 0.9), sash=(0.25, 0.45, 0.85))),
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
        key_pose(arm, f, compose(BASE, {
            'chest': R(x=-0.025 * br), 'neck': R(x=0.02 * br), 'head': R(z=0.05 * math.sin(p * 0.5), x=0.01 * br),
            'upper_arm.L': R(y=-0.03 * br), 'upper_arm.R': R(y=0.03 * br),
            'cape.1': R(x=0.03 + 0.02 * br), 'cape.2': R(x=0.02 * br),
        }), hip_dz=-0.004 * (1 - br) * 0.5)

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
