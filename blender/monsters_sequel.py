# -*- coding: utf-8 -*-
"""第二部の島のモンスター（build_monsters.py の最後で実行される。関数・マテリアルはそちらのものを使う）
  灼砂：サソリ・ミイラ・サボテン・アヌビス（ボス）
  氷雪：ゆきだるま・ペンギンナイト・イエティ（中ボス）
  炎獄：サラマンダー・ひのとり・イフリート（ボス）
  闇  ：やみのきし・デビルアイ・ゼノス（最後のボス）
"""


def bat_wing(mb, sx, scale, arm_m, mem_m, claw_m=None, tatter=0.0, seed=0):
    """コウモリ型の翼（腕の骨＋指＋膜）。原点が付け根"""
    rng = random.Random(seed)
    S = scale
    arm = [Vector((0, 0, 0.05 * S)), Vector((0.35 * sx * S, 0.12 * S, 0.27 * S)), Vector((0.6 * sx * S, 0.18 * S, 0.4 * S))]
    mb.tube(arm, [0.045 * S, 0.038 * S, 0.03 * S], arm_m, seg=8)
    hand = arm[-1]
    fingers = [Vector((1.05 * sx, 0.2, 0.47)) * S, Vector((1.15 * sx, 0.2, 0.1)) * S, Vector((0.95 * sx, 0.2, -0.2)) * S, Vector((0.6 * sx, 0.15, -0.3)) * S]
    for f in fingers:
        mb.tube([hand, hand.lerp(f, 0.5) + Vector((0, 0, 0.03 * S)), f], [0.024 * S, 0.016 * S, 0.006 * S], arm_m, seg=6)
    if claw_m:
        cone_to(mb, claw_m, hand, (0.3 * sx, 0, 1), 0.025 * S, 0.12 * S)
    outline = [Vector((0, 0.02 * S, 0.06 * S)), arm[1], hand, fingers[0]]
    prev = fingers[0]
    for f in fingers[1:]:
        mid = prev.lerp(f, 0.5).lerp(hand, 0.25 + tatter * rng.uniform(0, 0.25))
        outline += [mid, f]
        prev = f
    outline += [Vector((0.2 * sx, 0.08, -0.2)) * S, Vector((0, 0.02 * S, -0.12 * S))]
    cen = Vector((0.45 * sx, 0.1, 0.1)) * S
    verts = [tuple(cen)] + [tuple(v) for v in outline]
    mb.poly(verts, [(0, i, i + 1) for i in range(1, len(verts) - 1)], mem_m, smooth=True)


def wrap_rings(mb, surf, cx, cy, z0, z1, n, mats, r=0.022, rng=None, out=0.012):
    """包帯や鎧の帯：体の表面に沿って斜めに巻く輪"""
    rng = rng or random.Random(3)
    for k in range(n):
        z = z0 + (z1 - z0) * (k + 0.5) / n
        tilt = rng.uniform(-0.25, 0.25)
        pts = []
        for a in range(25):
            ang = a / 24 * math.tau
            p, d = surf.radial(Vector((cx, cy, z)), ang, tilt=tilt * math.sin(ang), maxd=1.5)
            pts.append(p + d * out)
        mb.tube(pts, [r] * len(pts), mats[k % len(mats)], seg=5, flat=0.45)


# ------------------------------------------------------------------ デザートスコーピオン
def build_scorpion(x):
    r = root("Mon_Scorpion", x)
    sh = mat("ScorpShell", (0.5, 0.3, 0.12), 0.35)
    shd = mat("ScorpShellDark", (0.2, 0.11, 0.05), 0.45)
    eyem = mat("ScorpEye", (1.0, 0.2, 0.1), 0.2, emit=(1.0, 0.15, 0.05), emit_strength=4.0)
    sting = mat("ScorpSting", (0.75, 0.9, 0.3), 0.3, emit=(0.5, 0.9, 0.1), emit_strength=1.2)
    el = [E_ell((0, -0.35, 0.45), 0.42, 0.38, 0.2), E_ell((0, -0.4, 0.52), 0.32, 0.28, 0.14)]
    for k in range(5):
        el.append(E_ell((0, 0.05 + k * 0.21, 0.45 - k * 0.012), 0.4 - k * 0.035, 0.13, 0.17 - k * 0.012))

    def a_body(c, n):
        if n.z < -0.3:
            return 1
        if c.y > -0.05 and ((c.y + 0.06) * 4.76) % 1.0 < 0.22:
            return 1
        return 0
    body, me = meta_part("Mon_Scorpion_Body", el, [sh, shd], res=0.012, faces=8000, assign=a_body, parent=r)
    mb = CMB()
    for s in (-1, 1):
        for (ex, ey, ez, er) in ((0.08, -0.6, 0.62, 0.05), (0.16, -0.58, 0.6, 0.035), (0.2, -0.52, 0.6, 0.03)):
            mb.add('sphere', eyem, loc=(s * ex, ey, ez), scale=(er, er, er))
        # 口のはさみ（鋏角）
        mb.tube([(s * 0.06, -0.68, 0.42), (s * 0.08, -0.82, 0.4), (s * 0.04, -0.9, 0.38)], [0.04, 0.03, 0.008], shd, seg=6)
    mb.build("Mon_Scorpion_Face", COLL, parent=body)
    # しっぽ（体の後ろから背中の上へ反り返る）
    tp = [Vector(v) for v in ((0, 0, 0), (0, 0.3, 0.25), (0, 0.4, 0.65), (0, 0.3, 1.05), (0, 0.05, 1.3), (0, -0.22, 1.36))]
    tel = []
    for k, p in enumerate(tp):
        tel.append(E_ball(p, 0.13 - k * 0.012))
    tel += E_chain(tp, [0.09 - k * 0.006 for k in range(len(tp))])
    tel.append(E_ell((0, -0.38, 1.3), 0.12, 0.15, 0.11))
    tail, _ = meta_part("Mon_Scorpion_Tail", tel, [sh, shd], res=0.009, faces=4000,
                        assign=lambda c, n: 1 if n.z < -0.5 else 0, parent=r, loc=(0, 1.0, 0.48))
    mb = CMB()
    cone_to(mb, sting, (0, -0.48, 1.26), (0, -0.7, -0.7), 0.06, 0.32, seg=8)
    mb.build("Mon_Scorpion_Stinger", COLL, parent=tail)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        for k in range(4):
            yk = -0.25 + k * 0.2
            mb.tube([(0, yk, 0), (sx * 0.35, yk, 0.25), (sx * 0.62, yk + 0.05, 0.05), (sx * 0.78, yk + 0.1, -0.4)], [0.05, 0.045, 0.035, 0.012], sh, seg=8)
            mb.add('sphere', shd, loc=(sx * 0.35, yk, 0.25), scale=(0.05, 0.05, 0.05))
            mb.add('sphere', shd, loc=(sx * 0.62, yk + 0.05, 0.05), scale=(0.04, 0.04, 0.04))
        mb.build(f"Mon_Scorpion_Legs{side}", COLL, loc=(sx * 0.28, -0.2, 0.42), parent=r)
        V_ = lambda a, b, c: Vector((sx * a, b, c))
        cel = E_chain([V_(0, 0, 0), V_(0.25, -0.25, 0.05), V_(0.3, -0.55, 0.1)], [0.07, 0.06, 0.06])
        cel += [E_ell(V_(0.32, -0.76, 0.12), 0.12, 0.2, 0.1)]
        cel += E_chain([V_(0.3, -0.92, 0.08), V_(0.27, -1.08, 0.08), V_(0.2, -1.18, 0.12)], [0.055, 0.04, 0.01])
        claw, _ = meta_part(f"Mon_Scorpion_Claw{side}", cel, [sh, shd], res=0.008, faces=3000,
                            assign=lambda c, n: 1 if c.y < -0.9 else 0, parent=r, loc=(sx * 0.3, -0.58, 0.45))
        meta_part(f"Mon_Scorpion_Pincer{side}", E_chain([Vector((0, 0, 0)), V_(-0.02, -0.17, 0.04), V_(-0.08, -0.28, -0.03)], [0.045, 0.035, 0.01]),
                  [shd], res=0.007, faces=1200, parent=claw, loc=tuple(V_(0.32, -0.9, 0.2)))


# ------------------------------------------------------------------ ミイラおとこ
def build_mummy(x):
    r = root("Mon_Mummy", x)
    cl = mat("MummyCloth", (0.8, 0.74, 0.6), 0.95)
    cld = mat("MummyClothDark", (0.52, 0.45, 0.35), 0.95)
    skin = mat("MummySkin", (0.22, 0.17, 0.12), 0.9)
    glow = mat("MummyEye", (1.0, 0.85, 0.2), 0.2, emit=(1.0, 0.75, 0.1), emit_strength=6.0)
    rag = mat("MummyRag", (0.74, 0.68, 0.54), 0.95, double=True)
    el = [E_ell((0, 0, 1.28), 0.21, 0.15, 0.3), E_ell((0, 0.01, 0.97), 0.17, 0.12, 0.13), E_cap((0, 0, 1.5), (0, 0, 1.62), 0.07)]
    for s in (-1, 1):
        el.append(E_ball((s * 0.19, 0, 1.5), 0.08))
    body, me = meta_part("Mon_Mummy_Body", el, [cl], res=0.008, faces=5000, parent=r)
    surf = Surface(me)
    mb = CMB()
    wrap_rings(mb, surf, 0, 0, 0.88, 1.58, 11, [cl, cld], r=0.024, rng=random.Random(5))
    rng = random.Random(7)
    for k in range(5):
        a = rng.uniform(0, math.tau)
        z = rng.uniform(0.9, 1.4)
        p, d = surf.radial(Vector((0, 0, z)), a, maxd=1)
        top = p + d * 0.02
        verts = [tuple(top + Vector((-0.03, 0, 0))), tuple(top + Vector((0.03, 0, 0))), tuple(top + d * 0.05 + Vector((0.035, 0, -0.35))), tuple(top + d * 0.05 + Vector((-0.02, 0, -0.32)))]
        mb.poly(verts, [(0, 1, 2, 3)], rag)
    mb.build("Mon_Mummy_Wraps", COLL, parent=body)
    hel = [E_ell((0, 0, 0.12), 0.11, 0.125, 0.13), E_ell((0, -0.04, 0.05), 0.09, 0.09, 0.08)]
    head, hme = meta_part("Mon_Mummy_Head", hel, [cl], res=0.006, faces=3000, parent=body, loc=(0, 0, 1.62))
    hs = Surface(hme)
    mb = CMB()
    wrap_rings(mb, hs, 0, 0, -0.02, 0.24, 7, [cl, cld], r=0.016, rng=random.Random(9), out=0.006)
    p, n = hs.ray(Vector((0, -1, 0.11)), Vector((0, 1, 0)))
    if p:
        e = basis_euler(n)
        mb.add('cube', skin, loc=p - n * 0.005, rot=e, scale=(0.15, 0.03, 0.035))
        for s in (-1, 1):
            mb.add('sphere', glow, loc=p + n * 0.01 + Vector((s * 0.035, 0, 0)), rot=e, scale=(0.016, 0.01, 0.012))
    mb.build("Mon_Mummy_Face", COLL, parent=head)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        pts = [Vector((0, 0, 0)), Vector((sx * 0.04, -0.3, -0.06)), Vector((sx * 0.04, -0.58, -0.04))]
        mb.tube(pts, [0.06, 0.052, 0.045], cl, seg=10)
        for k in range(7):
            p = pts[0].lerp(pts[2], (k + 0.5) / 7)
            mb.add('cyl', cld if k % 2 else cl, loc=tuple(p), rot=(math.pi / 2 - 0.1, 0, 0.1 * k), r1=0.064, r2=0.06, depth=0.045, seg=10)
        mb.add('sphere', cl, loc=(sx * 0.04, -0.64, -0.05), scale=(0.05, 0.06, 0.04))
        for k in range(4):
            mb.tube([(sx * (0.04 + (k - 1.5) * 0.02), -0.67, -0.05), (sx * (0.04 + (k - 1.5) * 0.024), -0.74, -0.08)], [0.012, 0.009], skin, seg=5)
        mb.poly([(sx * 0.02, -0.3, -0.1), (sx * 0.06, -0.3, -0.1), (sx * 0.08, -0.36, -0.42), (sx * 0.03, -0.34, -0.4)], [(0, 1, 2, 3)], rag)
        mb.build(f"Mon_Mummy_Arm{side}", COLL, loc=(sx * 0.22, 0, 1.48), parent=body)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        pts = [Vector((0, 0, 0)), Vector((0, 0.02, -0.44)), Vector((0, 0, -0.86))]
        mb.tube(pts, [0.075, 0.06, 0.05], cl, seg=10)
        for k in range(8):
            p = pts[0].lerp(pts[2], (k + 0.5) / 8)
            mb.add('cyl', cld if k % 2 else cl, loc=tuple(p), rot=(0.1 * ((k % 3) - 1), 0, 0), r1=0.08 - k * 0.003, r2=0.075 - k * 0.003, depth=0.05, seg=10)
        mb.add('sphere', cld, loc=(0, -0.05, -0.9), scale=(0.06, 0.12, 0.04))
        mb.build(f"Mon_Mummy_Leg{side}", COLL, loc=(sx * 0.1, 0, 0.93), parent=r)


# ------------------------------------------------------------------ トゲサボテン
def build_cactus(x):
    r = root("Mon_Cactus", x)
    cg = mat("CactusMon", (0.28, 0.55, 0.25), 0.7)
    cgd = mat("CactusMonDark", (0.17, 0.36, 0.16), 0.75)
    spine = mat("Spine", (0.95, 0.9, 0.7), 0.5)
    bloom = mat("CactusBloom", (1.0, 0.38, 0.58), 0.6)
    root_m = mat("CactusRoot", (0.42, 0.3, 0.18), 0.9)
    el = [E_cap((0, 0, 0.32), (0, 0, 1.0), 0.34), E_ell((0, 0, 0.3), 0.36, 0.34, 0.28)]

    def a(c, n):
        ang = math.atan2(c.x, -c.y)
        return 1 if ((ang / math.tau * 10) % 1.0) < 0.18 and abs(n.z) < 0.8 else 0
    body, me = meta_part("Mon_Cactus_Body", el, [cg, cgd], res=0.009, faces=6000, assign=a, parent=r)
    surf = Surface(me)
    mb = CMB()
    rng = random.Random(4)
    for k in range(70):
        ang = rng.uniform(0, math.tau)
        z = rng.uniform(0.2, 1.25)
        if abs(((ang + math.pi) % math.tau) - math.pi) < 0.55 and 0.45 < z < 1.0:
            continue
        p, d = surf.radial(Vector((0, 0, min(z, 1.0))), ang, tilt=max(0.0, z - 1.0) * 3, maxd=1)
        cone_to(mb, spine, p - d * 0.01, d + Vector((0, 0, 0.3)), 0.012, 0.11, seg=4)
    for s in (-1, 1):
        eye(mb, surf, s * 0.11, 0.78, 0.075, 0.085, iris=(0.1, 0.06, 0.03), pupil_scale=0.55, look=(-s * 0.2, -0.2))
        p, n = surf_point(surf, s * 0.11, 0.9)
        if p:
            mb.add('cube', cgd, loc=p + n * 0.012, rot=(0, s * 0.4, 0), scale=(0.13, 0.03, 0.03))
        mb.add('sphere', root_m, loc=(s * 0.18, -0.05, 0.03), scale=(0.11, 0.15, 0.06))
    p, n = surf_point(surf, 0, 0.58)
    if p:
        e = basis_euler(n)
        mb.add('sphere', M_MOUTH, loc=p - n * 0.01, rot=e, scale=(0.09, 0.025, 0.05))
        for s in (-1, 1):
            mb.add('cyl', M_TOOTH, loc=p + Vector((s * 0.035, -0.012, 0.035)), rot=(math.pi, 0, 0), r1=0.013, r2=0.0, depth=0.035, seg=5)
    for k in range(6):
        a_ = k / 6 * math.tau
        mb.add('sphere', bloom, loc=(math.cos(a_) * 0.11, math.sin(a_) * 0.11, 1.32), rot=(0, 0.5, a_), scale=(0.1, 0.05, 0.025))
    mb.add('sphere', mat("BloomCenter", (1.0, 0.85, 0.2), 0.5), loc=(0, 0, 1.34), scale=(0.06, 0.06, 0.03))
    mb.build("Mon_Cactus_Parts", COLL, parent=body)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.tube([(0, 0, 0), (sx * 0.22, 0, 0.0), (sx * 0.3, 0, 0.08), (sx * 0.32, 0, 0.36)], [0.13, 0.13, 0.12, 0.11], cg, seg=12)
        mb.add('sphere', cg, loc=(sx * 0.32, 0, 0.36), scale=(0.11, 0.11, 0.1))
        for k in range(10):
            ang = k * 2.39
            p = Vector((sx * 0.3 + math.cos(ang) * 0.12, math.sin(ang) * 0.12, 0.08 + (k % 5) * 0.07))
            cone_to(mb, spine, p, (math.cos(ang) * sx, math.sin(ang), 0.3), 0.01, 0.08, seg=4)
        mb.build(f"Mon_Cactus_Arm{side}", COLL, loc=(sx * 0.28, 0, 0.68), parent=body)


# ------------------------------------------------------------------ アヌビス（砂の魔将）
def build_anubis(x):
    r = root("Mon_Anubis", x)
    skin = mat("AnubisSkin", (0.07, 0.06, 0.08), 0.45)
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    blue = mat("AnubisBlue", (0.1, 0.2, 0.62), 0.5)
    white = mat("AnubisLinen", (0.93, 0.89, 0.78), 0.85)
    glow = mat("AnubisEye", (1.0, 0.8, 0.2), 0.2, emit=(1.0, 0.7, 0.1), emit_strength=7.0)
    el = [E_ell((0, 0, 1.75), 0.36, 0.22, 0.3), E_ell((0, -0.02, 1.42), 0.27, 0.18, 0.26), E_ell((0, 0, 1.12), 0.25, 0.17, 0.14),
          E_cap((0, 0, 1.95), (0, -0.02, 2.18), 0.12)]
    for s in (-1, 1):
        el += [E_ball((s * 0.4, 0, 1.92), 0.17), E_ell((s * 0.16, -0.1, 1.82), 0.16, 0.08, 0.13)]
    body, me = meta_part("Mon_Anubis_Body", el, [skin], res=0.012, faces=7000, parent=r)
    mb = CMB()
    # 腰布・ベルト・胸飾り
    mb.add('cyl', white, loc=(0, 0, 0.92), r1=0.42, r2=0.28, depth=0.5, seg=24)
    mb.add('cyl', gold, loc=(0, 0, 1.17), r1=0.29, r2=0.29, depth=0.08, seg=24)
    mb.add('cube', gold, loc=(0, -0.3, 0.92), rot=(0.12, 0, 0), scale=(0.18, 0.02, 0.48))
    for k in range(4):
        mb.add('cube', blue, loc=(0, -0.315, 1.08 - k * 0.12), rot=(0.12, 0, 0), scale=(0.19, 0.02, 0.04))
    for k, (rr, m_) in enumerate(((0.47, gold), (0.42, blue), (0.37, gold), (0.32, blue))):
        mb.add('cyl', m_, loc=(0, -0.02, 2.0 - k * 0.025), r1=rr, r2=rr - 0.02, depth=0.05, seg=28, scale=(1, 0.75, 1))
    mb.build("Mon_Anubis_Attire", COLL, parent=body)
    hel = [E_ell((0, 0.02, 0.12), 0.15, 0.17, 0.14), E_ell((0, -0.22, 0.06), 0.085, 0.18, 0.08), E_ell((0, -0.4, 0.03), 0.05, 0.1, 0.05),
           E_ell((0, -0.25, -0.03), 0.07, 0.14, 0.04)]
    for s in (-1, 1):
        hel.append(E_dir((s * 0.09, 0.06, 0.34), (s * 0.18, 0.12, 1), 0.24, 0.075, 0.03))
    head, hme = meta_part("Mon_Anubis_Head", hel, [skin], res=0.007, faces=4000, parent=body, loc=(0, -0.02, 2.2))
    hs = Surface(hme)
    mb = CMB()
    for s in (-1, 1):
        p, n = hs.ray(Vector((s * 0.08, -1, 0.15)), Vector((0, 1, 0)))
        if p:
            mb.add('sphere', glow, loc=p - n * 0.004, rot=basis_euler(n), scale=(0.04, 0.015, 0.018))
        # ネメス頭巾の垂れ布（青と金の縞）
        for k in range(6):
            z = 0.12 - k * 0.07
            mb.add('cube', blue if k % 2 else gold, loc=(s * 0.17, -0.02 - k * 0.012, z), rot=(0.1, 0, s * 0.12), scale=(0.1, 0.08, 0.07))
        mb.add('cube', gold, loc=(s * 0.095, 0.03, 0.42), rot=(0, s * -0.2, 0), scale=(0.02, 0.05, 0.25))
    mb.add('cyl', gold, loc=(0, 0.02, 0.2), r1=0.165, r2=0.16, depth=0.04, seg=24, scale=(1, 1.15, 1))
    mb.tube([(0, -0.16, 0.2), (0, -0.2, 0.28), (0, -0.17, 0.33)], [0.02, 0.018, 0.025], gold, seg=6)
    mb.add('sphere', M_PUPIL, loc=(0, -0.5, 0.05), scale=(0.035, 0.03, 0.03))
    mb.build("Mon_Anubis_HeadParts", COLL, parent=head)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.tube([(0, 0, 0), (sx * 0.06, 0, -0.4)], [0.105, 0.085], skin, seg=12)
        mb.tube([(sx * 0.06, 0, -0.4), (sx * 0.06, -0.26, -0.62)], [0.085, 0.07], skin, seg=12)
        mb.add('cyl', gold, loc=(sx * 0.06, -0.15, -0.53), rot=(math.pi / 2 - 0.7, 0, 0), r1=0.09, r2=0.085, depth=0.16, seg=14)
        mb.add('sphere', skin, loc=(sx * 0.06, -0.3, -0.66), scale=(0.07, 0.07, 0.08))
        if side == "R":
            # ワスの杖
            mb.tube([(sx * 0.06, -0.3, -1.95), (sx * 0.06, -0.3, 0.6)], [0.03, 0.03], gold, seg=8)
            mb.tube([(sx * 0.06, -0.3, 0.6), (sx * 0.06, -0.42, 0.7), (sx * 0.06, -0.48, 0.66)], [0.04, 0.035, 0.03], gold, seg=8)
            mb.add('ico', mat("ScarabGem", (0.2, 0.6, 1.0), 0.1, emit=(0.2, 0.5, 1.0), emit_strength=3.0), loc=(sx * 0.06, -0.38, 0.62), r=0.07, sub=1)
        mb.build(f"Mon_Anubis_Arm{side}", COLL, loc=(sx * 0.43, 0, 1.92), parent=body)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.tube([(0, 0, 0), (0, -0.02, -0.5)], [0.12, 0.095], skin, seg=12)
        mb.tube([(0, -0.02, -0.5), (0, 0.02, -1.0)], [0.09, 0.065], skin, seg=12)
        mb.add('cyl', gold, loc=(0, 0.01, -0.92), r1=0.08, r2=0.08, depth=0.08, seg=14)
        mb.add('sphere', mat("Sandal", (0.4, 0.26, 0.12), 0.8), loc=(0, -0.07, -1.05), scale=(0.08, 0.15, 0.04))
        mb.build(f"Mon_Anubis_Leg{side}", COLL, loc=(sx * 0.13, 0, 1.08), parent=r)


# ------------------------------------------------------------------ ゆきだるまん
def build_snowman(x):
    r = root("Mon_Snowman", x)
    snow = mat("SnowBody", (0.95, 0.97, 1.0), 0.85)
    coal = mat("Coal", (0.04, 0.04, 0.05), 0.6)
    carrot = mat("Carrot", (1.0, 0.48, 0.1), 0.6)
    scarf = mat("Scarf", (0.8, 0.1, 0.12), 0.9, double=True)
    bucket = mat("Bucket", (0.42, 0.42, 0.48), 0.4, 0.7)
    twig = mat("Twig", (0.3, 0.2, 0.12), 0.9)
    body, me = meta_part("Mon_Snowman_Body", [E_ball((0, 0, 0.45), 0.46), E_ball((0, 0, 1.02), 0.33)], [snow], res=0.012, faces=5000, parent=r)
    surf = Surface(me)
    mb = CMB()
    for k in range(3):
        p, n = surf_point(surf, 0, 0.92 + k * 0.14)
        if p:
            mb.add('sphere', coal, loc=p, rot=basis_euler(n), scale=(0.04, 0.03, 0.04))
    # マフラー
    ring = [Vector((math.sin(a / 20 * math.tau) * 0.24, -math.cos(a / 20 * math.tau) * 0.24, 1.3)) for a in range(21)]
    mb.tube(ring, [0.07] * 21, scarf, seg=8, flat=0.6)
    mb.poly([(0.1, -0.24, 1.28), (0.2, -0.22, 1.28), (0.26, -0.3, 0.85), (0.15, -0.32, 0.86)], [(0, 1, 2, 3)], scarf)
    mb.build("Mon_Snowman_Parts", COLL, parent=body)
    head, hme = meta_part("Mon_Snowman_Head", [E_ball((0, 0, 0.2), 0.26)], [snow], res=0.008, faces=2500, parent=body, loc=(0, 0, 1.3))
    hs = Surface(hme)
    mb = CMB()
    for s in (-1, 1):
        p, n = hs.ray(Vector((s * 0.09, -1, 0.26)), Vector((0, 1, 0)))
        if p:
            mb.add('sphere', coal, loc=p, rot=basis_euler(n), scale=(0.04, 0.025, 0.05))
            mb.add('cube', coal, loc=p + Vector((-s * 0.01, -0.01, 0.07)), rot=(0, s * 0.45, 0), scale=(0.09, 0.02, 0.02))
    p, n = hs.ray(Vector((0, -1, 0.18)), Vector((0, 1, 0)))
    if p:
        cone_to(mb, carrot, p - n * 0.02, (0, -1, -0.05), 0.045, 0.24, seg=8)
    for k in range(5):
        a = (k - 2) * 0.32
        p, n = hs.ray(Vector((math.sin(a) * 0.12, -1, 0.06 - math.cos(a) * 0.03 + 0.03)), Vector((0, 1, 0)))
        if p:
            mb.add('sphere', coal, loc=p, scale=(0.022, 0.022, 0.022))
    mb.add('cyl', bucket, loc=(0.03, 0.02, 0.48), rot=(0.12, -0.2, 0), r1=0.2, r2=0.16, depth=0.24, seg=18)
    mb.add('cyl', bucket, loc=(0.0, 0.0, 0.37), rot=(0.12, -0.2, 0), r1=0.22, r2=0.22, depth=0.02, seg=18)
    mb.build("Mon_Snowman_Face", COLL, parent=head)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.tube([(0, 0, 0), (sx * 0.3, 0, 0.08), (sx * 0.55, 0, 0.22)], [0.03, 0.022, 0.012], twig, seg=6)
        mb.tube([(sx * 0.4, 0, 0.13), (sx * 0.5, 0, 0.3), (sx * 0.55, 0, 0.36)], [0.014, 0.01, 0.005], twig, seg=5)
        mb.tube([(sx * 0.5, 0, 0.19), (sx * 0.64, 0, 0.16)], [0.01, 0.005], twig, seg=5)
        mb.build(f"Mon_Snowman_Arm{side}", COLL, loc=(sx * 0.3, 0, 1.08), parent=body)


# ------------------------------------------------------------------ ペンギンナイト
def build_penguin(x):
    r = root("Mon_Penguin", x)
    blk = mat("PenguinBlack", (0.07, 0.08, 0.11), 0.4)
    wht = mat("PenguinWhite", (0.95, 0.95, 0.97), 0.6)
    beak = mat("PenguinBeak", (1.0, 0.6, 0.1), 0.5)
    steel = mat("IceSteel", (0.62, 0.76, 0.9), 0.3, 0.7)
    icec = mat("IceCrystal", (0.62, 0.86, 1.0), 0.08, emit=(0.35, 0.7, 1.0), emit_strength=2.0)
    shaft = mat("Wood", (0.42, 0.27, 0.14), 0.8)
    el = [E_ell((0, 0, 0.55), 0.3, 0.27, 0.45), E_ball((0, -0.02, 1.02), 0.21)]

    def a(c, n):
        return 1 if (n.y < -0.25 and 0.2 < c.z < 0.92 and abs(c.x) < 0.22) else 0
    body, me = meta_part("Mon_Penguin_Body", el, [blk, wht], res=0.01, faces=5000, assign=a, parent=r)
    surf = Surface(me)
    mb = CMB()
    for s in (-1, 1):
        eye(mb, surf, s * 0.075, 1.06, 0.05, 0.055, iris=(0.1, 0.05, 0.03), pupil_scale=0.6, look=(-s * 0.2, 0), y0=-2)
        mb.add('sphere', beak, loc=(s * 0.1, -0.06, 0.03), scale=(0.08, 0.15, 0.03))
        p, n = surf_point(surf, s * 0.08, 1.12)
        if p:
            mb.add('cube', blk, loc=p + n * 0.01, rot=(0, s * 0.5, 0), scale=(0.08, 0.02, 0.02))
    p, n = surf_point(surf, 0, 0.98)
    if p:
        cone_to(mb, beak, p - n * 0.03, (0, -1, -0.15), 0.06, 0.16, seg=8)
    # 兜
    mb.add('sphere', steel, loc=(0, 0.0, 1.12), scale=(0.23, 0.24, 0.16))
    mb.add('cyl', steel, loc=(0, 0.0, 1.07), r1=0.235, r2=0.235, depth=0.04, seg=20)
    mb.add('cube', mat("ClothBlue", (0.15, 0.3, 0.6), 0.9, double=True), loc=(0, 0.04, 1.33), scale=(0.03, 0.3, 0.12))
    mb.build("Mon_Penguin_Parts", COLL, parent=body)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        fl, _ = None, None
        mb.add('sphere', blk, loc=(sx * 0.05, 0, -0.22), rot=(0, sx * 0.25, 0), scale=(0.05, 0.12, 0.26))
        if side == "R":
            mb.tube([(sx * 0.1, -0.15, -0.9), (sx * 0.1, -0.15, 0.55)], [0.022, 0.022], shaft, seg=6)
            cone_to(mb, icec, (sx * 0.1, -0.15, 0.55), (0, 0, 1), 0.06, 0.32, seg=4)
        else:
            mb.add('cyl', steel, loc=(sx * 0.16, -0.06, -0.2), rot=(0, sx * math.pi / 2, -sx * 0.5), r1=0.18, r2=0.18, depth=0.03, seg=20)
            mb.add('sphere', icec, loc=(sx * 0.18, -0.08, -0.2), scale=(0.05, 0.05, 0.05))
        mb.build(f"Mon_Penguin_Arm{side}", COLL, loc=(sx * 0.27, 0, 0.82), parent=body)


# ------------------------------------------------------------------ イエティ（中ボス）
def build_yeti(x):
    r = root("Mon_Yeti", x)
    fur = mat("YetiFur", (0.9, 0.93, 0.97), 0.95)
    fur2 = mat("YetiFurShade", (0.72, 0.78, 0.88), 0.95)
    skin = mat("YetiSkin", (0.42, 0.52, 0.68), 0.6)
    horn = mat("Horn", (0.93, 0.89, 0.78), 0.45)
    glow = mat("YetiEye", (0.4, 0.9, 1.0), 0.2, emit=(0.3, 0.85, 1.0), emit_strength=5.0)
    el = [E_ell((0, 0.05, 1.35), 0.55, 0.45, 0.6), E_ell((0, -0.1, 1.05), 0.45, 0.38, 0.38), E_ell((0, 0.1, 1.8), 0.5, 0.4, 0.3),
          E_ell((0, -0.25, 1.95), 0.26, 0.26, 0.25)]
    rng = random.Random(8)
    for k in range(26):
        a = rng.uniform(-2.6, 2.6)
        z = rng.uniform(0.9, 2.05)
        d = Vector((math.sin(a), math.cos(a) * 0.9, rng.uniform(-0.2, 0.5))).normalized()
        el.append(E_dir(Vector((math.sin(a) * 0.48, 0.05 + math.cos(a) * 0.38, z)), d, 0.22, 0.09, 0.07))
    for s in (-1, 1):
        el += [E_cap((s * 0.25, 0, 0.8), (s * 0.28, -0.05, 0.3), 0.2), E_ell((s * 0.28, -0.12, 0.12), 0.15, 0.22, 0.1)]

    def a_(c, n):
        if c.z > 1.82 and c.y < -0.38 and abs(c.x) < 0.2:
            return 2
        if c.z < 0.2:
            return 2
        return 1 if n.z < -0.3 else 0
    body, me = meta_part("Mon_Yeti_Body", el, [fur, fur2, skin], res=0.016, faces=12000, assign=a_, parent=r)
    surf = Surface(me)
    mb = CMB()
    for s in (-1, 1):
        p, n = surf.ray(Vector((s * 0.09, -3, 2.0)), Vector((0, 1, 0)))
        if p:
            mb.add('sphere', glow, loc=p - n * 0.005, rot=basis_euler(n), scale=(0.045, 0.02, 0.03))
            mb.add('cube', fur2, loc=p + n * 0.02 + Vector((0, 0, 0.05)), rot=(0, s * 0.35, 0), scale=(0.12, 0.05, 0.04))
        mb.tube([(s * 0.16, -0.2, 2.15), (s * 0.3, -0.15, 2.3), (s * 0.36, -0.25, 2.42)], [0.06, 0.04, 0.01], horn, seg=8)
        for k in (-1, 0, 1):
            cone_to(mb, horn, (s * 0.28 + k * 0.06, -0.3, 0.06), (k * 0.2, -1, -0.2), 0.02, 0.09)
    p, n = surf.ray(Vector((0, -3, 1.86)), Vector((0, 1, 0)))
    if p:
        e = basis_euler(n)
        mb.add('sphere', M_MOUTH, loc=p - n * 0.01, rot=e, scale=(0.12, 0.03, 0.05))
        for s in (-1, 1):
            mb.add('cyl', M_TOOTH, loc=p + Vector((s * 0.06, -0.01, 0.0)), rot=(0, 0, 0), r1=0.02, r2=0.0, depth=0.07, seg=5)
    mb.build("Mon_Yeti_Parts", COLL, parent=body)
    for side, sx in (("L", 1), ("R", -1)):
        ael = [E_cap((0, 0, 0), (sx * 0.15, -0.05, -0.6), 0.2), E_cap((sx * 0.15, -0.05, -0.6), (sx * 0.15, -0.22, -1.12), 0.17),
               E_ell((sx * 0.15, -0.26, -1.25), 0.15, 0.13, 0.13)]
        for k in range(6):
            ael.append(E_dir((sx * (0.12 + 0.02 * k), 0.08, -0.1 - k * 0.17), (sx, 0.4, -0.3), 0.16, 0.07, 0.05))
        arm, ame = meta_part(f"Mon_Yeti_Arm{side}", ael, [fur, fur2, skin], res=0.014, faces=4000,
                             assign=lambda c, n: 2 if c.z < -1.15 else (1 if n.z < -0.3 else 0), parent=r, loc=(sx * 0.62, 0.05, 1.85))
        mb = CMB()
        for k in (-1, 0, 1):
            cone_to(mb, horn, (sx * 0.15 + k * 0.06, -0.36, -1.3), (k * 0.2, -0.8, -0.6), 0.02, 0.1)
        mb.build(f"Mon_Yeti_Claws{side}", COLL, parent=arm)


# ------------------------------------------------------------------ サラマンダー
def build_lizard(x):
    r = root("Mon_Lizard", x)
    sc = mat("SalaScale", (0.85, 0.28, 0.1), 0.45)
    scd = mat("SalaDark", (0.42, 0.09, 0.05), 0.5)
    belly = mat("SalaBelly", (1.0, 0.75, 0.3), 0.6)
    core = mat("FlameCore", (1.0, 0.86, 0.45), 0.4, emit=(1.0, 0.75, 0.3), emit_strength=2.6)
    mid = mat("FlameMid", (1.0, 0.45, 0.1), 0.4, emit=(1.0, 0.36, 0.05), emit_strength=2.8)
    el = [E_ell((0, 0, 0.45), 0.28, 0.58, 0.22), E_ell((0, -0.4, 0.5), 0.22, 0.25, 0.2), E_cap((0, -0.45, 0.5), (0, -0.62, 0.55), 0.14)]

    def a(c, n):
        if n.z < -0.3:
            return 2
        return 1 if n.z > 0.75 and abs(c.x) < 0.08 else 0
    body, me = meta_part("Mon_Lizard_Body", el, [sc, scd, belly], res=0.011, faces=6000, assign=a, parent=r)
    mb = CMB()
    for k in range(9):
        cone_to(mb, scd, (0, -0.55 + k * 0.13, 0.66 - abs(k - 3) * 0.012), (0, 0.4, 1), 0.04, 0.14, seg=5)
    mb.build("Mon_Lizard_Spikes", COLL, parent=body)
    hel = [E_ell((0, -0.12, 0.02), 0.13, 0.22, 0.09), E_ell((0, 0.02, 0.04), 0.14, 0.12, 0.11), E_ell((0, -0.14, -0.06), 0.11, 0.18, 0.04)]
    head, hme = meta_part("Mon_Lizard_Head", hel, [sc, scd, belly], res=0.006, faces=3000,
                          assign=lambda c, n: 2 if n.z < -0.4 else (1 if n.z > 0.7 else 0), parent=body, loc=(0, -0.68, 0.57))
    hs = Surface(hme)
    mb = CMB()
    for s in (-1, 1):
        p, n = hs.ray(Vector((s * 1.0, -0.04, 0.07)), Vector((-s, 0, 0)))
        if p:
            e = basis_euler((n + Vector((0, -0.5, 0.2))).normalized())
            mb.add('sphere', mat("SalaIris", (1.0, 0.85, 0.1), 0.15, emit=(1.0, 0.7, 0.05), emit_strength=2.0), loc=p - n * 0.006, rot=e, scale=(0.035, 0.02, 0.03))
            mb.add('sphere', M_PUPIL, loc=p + n * 0.006, rot=e, scale=(0.008, 0.012, 0.026))
        mb.tube([(s * 0.08, 0.08, 0.1), (s * 0.15, 0.2, 0.16), (s * 0.18, 0.3, 0.14)], [0.025, 0.015, 0.003], scd, seg=6)
        mb.add('sphere', M_PUPIL, loc=(s * 0.03, -0.33, 0.04), scale=(0.01, 0.008, 0.008))
    mb.add('sphere', M_MOUTH, loc=(0, -0.2, -0.04), scale=(0.1, 0.16, 0.01))
    mb.build("Mon_Lizard_HeadParts", COLL, parent=head)
    tp = [Vector(v) for v in ((0, 0, 0), (0, 0.3, -0.05), (0.05, 0.6, -0.15), (0.12, 0.9, -0.22), (0.15, 1.15, -0.2))]
    tail, _ = meta_part("Mon_Lizard_Tail", E_chain(tp, [0.15, 0.12, 0.09, 0.06, 0.03]), [sc, scd, belly], res=0.009, faces=2500,
                        assign=lambda c, n: 2 if n.z < -0.3 else 0, parent=body, loc=(0, 0.55, 0.42))
    mb = CMB()
    tip = tp[-1]
    for k in range(5):
        a_ = k / 5 * math.tau
        pts = [tip + Vector((math.cos(a_) * 0.04, math.sin(a_) * 0.04, 0)) + Vector((math.cos(a_ + t) * 0.03 * t, math.sin(a_ + t) * 0.03 * t, 0.07 + t * 0.32)) for t in [j / 4 for j in range(5)]]
        mb.tube(pts, [0.07 * (1 - j / 4) + 0.004 for j in range(5)], mid if k % 2 else core, seg=8)
    mb.build("Mon_Lizard_Flame", COLL, parent=tail)

    def leg(name, pivot, sx):
        lel = [E_cap((0, 0, 0), (sx * 0.22, 0, -0.04), 0.08), E_cap((sx * 0.22, 0, -0.04), (sx * 0.3, -0.05, -0.36), 0.06),
               E_ell((sx * 0.32, -0.1, -0.4), 0.07, 0.1, 0.035)]
        ob, _ = meta_part(name, lel, [sc, scd], res=0.007, faces=1500, assign=lambda c, n: 1 if c.z < -0.3 else 0, parent=r, loc=pivot)
        mb = CMB()
        for k in (-1, 0, 1):
            cone_to(mb, M_CLAW, (sx * 0.32 + k * 0.03, -0.18, -0.41), (k * 0.3, -1, -0.3), 0.012, 0.06)
        mb.build(name + "Claws", COLL, parent=ob)
    leg("Mon_Lizard_LegFL", (0.2, -0.32, 0.42), 1)
    leg("Mon_Lizard_LegFR", (-0.2, -0.32, 0.42), -1)
    leg("Mon_Lizard_LegBL", (0.2, 0.32, 0.42), 1)
    leg("Mon_Lizard_LegBR", (-0.2, 0.32, 0.42), -1)


# ------------------------------------------------------------------ ひのとり
def build_firebird(x):
    r = root("Mon_Firebird", x)
    red = mat("PhoenixRed", (1.0, 0.3, 0.08), 0.5, emit=(1.0, 0.25, 0.05), emit_strength=0.9)
    gold = mat("PhoenixGold", (1.0, 0.75, 0.2), 0.4, emit=(1.0, 0.65, 0.15), emit_strength=1.4)
    dark = mat("PhoenixDark", (0.5, 0.08, 0.05), 0.6)
    beak = mat("PhoenixBeak", (1.0, 0.85, 0.35), 0.4)
    el = [E_ell((0, 0, 0), 0.22, 0.38, 0.24), E_ell((0, -0.38, 0.22), 0.13, 0.15, 0.13), E_cap((0, -0.15, 0.08), (0, -0.33, 0.2), 0.12)]
    body, me = meta_part("Mon_Firebird_Body", el, [red, gold], res=0.008, faces=4000, assign=lambda c, n: 1 if n.z < -0.3 else 0, parent=r, loc=(0, 0, 1.55))
    hs = Surface(me)
    mb = CMB()
    cone_to(mb, beak, (0, -0.5, 0.22), (0, -1, -0.25), 0.05, 0.18, seg=8)
    for s in (-1, 1):
        p, n = hs.ray(Vector((s * 1.0, -0.4, 0.27)), Vector((-s, 0, 0)))
        if p:
            mb.add('sphere', M_PUPIL, loc=p, rot=basis_euler(n), scale=(0.03, 0.015, 0.03))
            mb.add('sphere', M_EYEW, loc=p + n * 0.01 + Vector((0, -0.01, 0.012)), rot=basis_euler(n), scale=(0.008, 0.005, 0.008))
    for k in range(5):
        a = (k - 2) * 0.25
        mb.tube([(0, -0.38, 0.33), (math.sin(a) * 0.08, -0.3, 0.5), (math.sin(a) * 0.15, -0.1, 0.62 - abs(k - 2) * 0.05)], [0.025, 0.02, 0.004], gold, seg=6)
    for s in (-1, 1):
        mb.tube([(s * 0.08, 0.05, -0.2), (s * 0.08, 0.0, -0.42)], [0.02, 0.015], beak, seg=6)
        for k in (-1, 0, 1):
            cone_to(mb, beak, (s * 0.08 + k * 0.02, -0.02, -0.43), (k * 0.4, -1, -0.3), 0.01, 0.06)
    mb.build("Mon_Firebird_Parts", COLL, parent=body)
    # 長い尾羽
    mb = CMB()
    for k in range(5):
        a = (k - 2) * 0.22
        pts = [Vector((0, 0, 0)), Vector((math.sin(a) * 0.15, 0.4, -0.15)), Vector((math.sin(a) * 0.35, 0.85, -0.35)), Vector((math.sin(a) * 0.5, 1.25, -0.4))]
        mb.tube(pts, [0.05, 0.04, 0.03, 0.01], red if k % 2 else gold, seg=6, flat=0.3)
        mb.add('sphere', gold, loc=tuple(pts[-1]), scale=(0.08, 0.12, 0.02))
    mb.build("Mon_Firebird_Tail", COLL, loc=(0, 0.35, 1.5), parent=r)
    fred = mat("PhoenixFeather", (1.0, 0.32, 0.08), 0.5, emit=(1.0, 0.25, 0.05), emit_strength=0.9, double=True)
    fgold = mat("PhoenixFeatherGold", (1.0, 0.75, 0.2), 0.4, emit=(1.0, 0.65, 0.15), emit_strength=1.4, double=True)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        arm = [Vector((0, 0, 0)), Vector((sx * 0.35, 0.05, 0.12)), Vector((sx * 0.62, 0.1, 0.12))]
        mb.tube(arm, [0.05, 0.04, 0.03], red, seg=8)
        for k in range(11):
            t = k / 10
            base = arm[0].lerp(arm[2], 0.15 + t * 0.85)
            ln = 0.35 + 0.55 * math.sin(t * 2.4)
            tipv = base + Vector((sx * ln * (0.3 + t * 0.7), 0.1 + ln * (1 - t) * 0.9, -0.04))
            w = 0.09 + 0.03 * t
            side_v = Vector((0, 0, 1)).cross((tipv - base).normalized()).normalized()
            verts = [tuple(base + side_v * w * 0.5), tuple(base - side_v * w * 0.5), tuple(tipv - side_v * w * 0.35), tuple(tipv + side_v * w * 0.35)]
            mb.poly(verts, [(0, 1, 2, 3)], fgold if k > 6 else fred, smooth=True)
        mb.build(f"Mon_Firebird_Wing{side}", COLL, loc=(sx * 0.15, 0, 1.62), parent=r)


# ------------------------------------------------------------------ イフリート（炎の魔将）
def build_ifrit(x):
    r = root("Mon_Ifrit", x)
    skin = mat("IfritSkin", (0.55, 0.12, 0.06), 0.5)
    skd = mat("IfritDark", (0.25, 0.05, 0.03), 0.6)
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    core = mat("FlameCore", (1.0, 0.86, 0.45), 0.4, emit=(1.0, 0.75, 0.3), emit_strength=2.6)
    mid = mat("FlameMid", (1.0, 0.45, 0.1), 0.4, emit=(1.0, 0.36, 0.05), emit_strength=2.8)
    glow = mat("IfritEye", (1.0, 0.92, 0.4), 0.2, emit=(1.0, 0.85, 0.3), emit_strength=8.0)
    hornm = mat("IfritHorn", (0.15, 0.1, 0.08), 0.4)
    el = [E_ell((0, 0, 2.2), 0.55, 0.35, 0.45), E_ell((0, -0.02, 1.75), 0.4, 0.28, 0.35), E_ell((0, 0, 1.35), 0.32, 0.24, 0.25),
          E_ell((0, 0, 1.0), 0.22, 0.18, 0.25), E_ell((0, 0.05, 0.7), 0.13, 0.11, 0.2), E_cap((0, 0, 2.5), (0, -0.04, 2.75), 0.17)]
    for s in (-1, 1):
        el += [E_ball((s * 0.62, 0, 2.45), 0.3), E_ell((s * 0.22, -0.18, 2.25), 0.22, 0.1, 0.18)]

    def a(c, n):
        return 1 if c.z < 1.2 or n.z < -0.4 else 0
    body, me = meta_part("Mon_Ifrit_Body", el, [skin, skd], res=0.016, faces=9000, assign=a, parent=r)
    mb = CMB()
    mb.add('cyl', gold, loc=(0, 0, 1.55), r1=0.34, r2=0.32, depth=0.12, seg=24)
    mb.add('ico', mat("RubyFire", (1.0, 0.2, 0.05), 0.1, emit=(1.0, 0.2, 0.05), emit_strength=3), loc=(0, -0.33, 1.55), r=0.08, sub=1)
    # 下半身は渦巻く炎
    rng = random.Random(12)
    for k in range(12):
        a_ = k / 12 * math.tau
        pts = []
        for j in range(7):
            t = j / 6
            aa = a_ + t * 2.2
            rad = 0.32 * (1 - t * 0.7)
            pts.append(Vector((math.cos(aa) * rad, math.sin(aa) * rad, 1.15 - t * 0.95)))
        mb.tube(pts, [0.13 * (1 - j / 6 * 0.85) for j in range(7)], mid if k % 2 else core, seg=8)
    mb.build("Mon_Ifrit_Flame", COLL, parent=body)
    hel = [E_ell((0, 0, 0.12), 0.2, 0.2, 0.2), E_ell((0, -0.12, 0.02), 0.16, 0.12, 0.13), E_ell((0, -0.13, -0.08), 0.13, 0.11, 0.06),
           E_ell((0, -0.16, 0.16), 0.17, 0.05, 0.04)]
    head, hme = meta_part("Mon_Ifrit_Head", hel, [skin, skd], res=0.007, faces=4000, assign=lambda c, n: 1 if c.z > 0.25 else 0, parent=body, loc=(0, -0.04, 2.82))
    hs = Surface(hme)
    mb = CMB()
    for s in (-1, 1):
        p, n = hs.ray(Vector((s * 0.07, -1, 0.1)), Vector((0, 1, 0)))
        if p:
            mb.add('sphere', glow, loc=p - n * 0.004, rot=basis_euler(n), scale=(0.04, 0.015, 0.02))
        mb.tube([(s * 0.15, 0, 0.22), (s * 0.35, 0.05, 0.38), (s * 0.42, 0.12, 0.62), (s * 0.36, 0.2, 0.78)], [0.07, 0.055, 0.03, 0.004], hornm, seg=10)
        mb.add('cyl', M_TOOTH, loc=(s * 0.05, -0.23, -0.06), rot=(0, 0, 0), r1=0.02, r2=0.0, depth=0.08, seg=5)
    mb.add('sphere', M_MOUTH, loc=(0, -0.22, -0.08), scale=(0.1, 0.04, 0.03))
    for k in range(9):
        a_ = (k - 4) * 0.28
        pts = [Vector((math.sin(a_) * 0.12, 0.05, 0.22)) + Vector((math.sin(a_) * 0.1 * t, 0.15 * t, 0.45 * t)) for t in [j / 4 for j in range(5)]]
        mb.tube(pts, [0.07 * (1 - j / 4) + 0.004 for j in range(5)], mid if k % 2 else core, seg=8)
    mb.build("Mon_Ifrit_Hair", COLL, parent=head)
    for side, sx in (("L", 1), ("R", -1)):
        ael = [E_cap((0, 0, 0), (sx * 0.18, -0.08, -0.62), 0.2), E_cap((sx * 0.18, -0.08, -0.62), (sx * 0.1, -0.4, -1.05), 0.17),
               E_ell((sx * 0.08, -0.46, -1.15), 0.16, 0.15, 0.15)]
        arm, _ = meta_part(f"Mon_Ifrit_Arm{side}", ael, [skin, skd], res=0.012, faces=3000, parent=body, loc=(sx * 0.72, 0, 2.48))
        mb = CMB()
        mb.add('cyl', gold, loc=(sx * 0.14, -0.27, -0.88), rot=(0.75, 0, 0), r1=0.16, r2=0.15, depth=0.2, seg=16)
        for k in range(5):
            a_ = k / 5 * math.tau
            p0 = Vector((sx * 0.08, -0.46, -1.15))
            pts = [p0 + Vector((math.cos(a_) * 0.12, math.sin(a_) * 0.12, 0.05)) + Vector((0, 0, t * 0.35)) for t in [j / 3 for j in range(4)]]
            mb.tube(pts, [0.06, 0.045, 0.025, 0.004], core if k % 2 else mid, seg=6)
        mb.build(f"Mon_Ifrit_ArmParts{side}", COLL, parent=arm)


# ------------------------------------------------------------------ やみのきし
def build_darkknight(x):
    r = root("Mon_DarkKnight", x)
    armor = mat("KnightArmor", (0.16, 0.15, 0.2), 0.35, 0.85)
    trim = mat("KnightTrim", (0.75, 0.72, 0.8), 0.3, 0.9)
    cape = mat("KnightCape", (0.35, 0.05, 0.08), 0.85, double=True)
    eyeg = mat("KnightEye", (1.0, 0.15, 0.1), 0.2, emit=(1.0, 0.1, 0.05), emit_strength=7.0)
    blade = mat("KnightBlade", (0.6, 0.62, 0.7), 0.3, 0.9)
    el = [E_ell((0, 0, 1.38), 0.3, 0.2, 0.3), E_ell((0, -0.03, 1.12), 0.24, 0.17, 0.16), E_ell((0, 0, 0.95), 0.22, 0.16, 0.1),
          E_ell((0, -0.12, 1.42), 0.24, 0.1, 0.2)]
    body, me = meta_part("Mon_DarkKnight_Body", el, [armor], res=0.009, faces=5000, parent=r)
    surf = Surface(me)
    mb = CMB()
    wrap_rings(mb, surf, 0, 0, 1.0, 1.65, 3, [trim], r=0.018, rng=random.Random(2), out=0.004)
    # 腰の草摺
    for k in range(8):
        a_ = k / 8 * math.tau
        mb.add('cube', armor, loc=(math.sin(a_) * 0.24, -math.cos(a_) * 0.18, 0.82), rot=(math.cos(a_) * 0.25, -math.sin(a_) * 0.25, -a_), scale=(0.16, 0.03, 0.3))
        mb.add('cube', trim, loc=(math.sin(a_) * 0.25, -math.cos(a_) * 0.19, 0.69), rot=(math.cos(a_) * 0.25, -math.sin(a_) * 0.25, -a_), scale=(0.17, 0.035, 0.03))
    p, n = surf_point(surf, 0, 1.4)
    if p:
        mb.add('ico', eyeg, loc=p + n * 0.02, r=0.05, sub=1)
    mb.build("Mon_DarkKnight_Plates", COLL, parent=body)
    # マント
    mb = CMB()
    verts, faces = [], []
    W, Hn = 9, 8
    for j in range(Hn + 1):
        t = j / Hn
        for i in range(W + 1):
            u = i / W - 0.5
            xx = u * (0.5 + 0.35 * t)
            yy = 0.02 + 0.08 * t + 0.04 * math.sin(u * 6 + t * 3)
            zz = -t * 1.3 - (0.05 * math.sin(i * 1.7) if j == Hn else 0)
            verts.append((xx, yy, zz))
    for j in range(Hn):
        for i in range(W):
            a_ = j * (W + 1) + i
            faces.append((a_, a_ + 1, a_ + W + 2, a_ + W + 1))
    mb.poly(verts, faces, cape, smooth=True)
    mb.build("Mon_DarkKnight_Cape", COLL, loc=(0, 0.2, 1.62), parent=body)
    hel = [E_ell((0, 0, 0.12), 0.13, 0.15, 0.14), E_ell((0, -0.06, 0.05), 0.11, 0.1, 0.1)]
    head, hme = meta_part("Mon_DarkKnight_Head", hel, [armor], res=0.006, faces=3000, parent=body, loc=(0, 0, 1.72))
    hs = Surface(hme)
    mb = CMB()
    p, n = hs.ray(Vector((0, -1, 0.1)), Vector((0, 1, 0)))
    if p:
        e = basis_euler(n)
        mb.add('cube', mat("Abyss", (0, 0, 0), 1.0), loc=p - n * 0.005, rot=e, scale=(0.17, 0.03, 0.035))
        for s in (-1, 1):
            mb.add('sphere', eyeg, loc=p + n * 0.006 + Vector((s * 0.045, 0, 0)), rot=e, scale=(0.022, 0.01, 0.012))
    mb.tube([(0, -0.14, 0.24), (0, 0.0, 0.32), (0, 0.18, 0.28)], [0.025, 0.03, 0.02], trim, seg=6, flat=3.0)
    for s in (-1, 1):
        mb.tube([(s * 0.12, -0.02, 0.18), (s * 0.24, 0.0, 0.3), (s * 0.28, 0.06, 0.45)], [0.03, 0.02, 0.004], trim, seg=8)
    mb.build("Mon_DarkKnight_Helm", COLL, parent=head)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.add('sphere', armor, loc=(sx * 0.05, 0, 0.04), scale=(0.17, 0.16, 0.12))
        mb.add('cyl', trim, loc=(sx * 0.05, 0, -0.02), r1=0.17, r2=0.17, depth=0.03, seg=16)
        for k in range(3):
            cone_to(mb, trim, (sx * (0.05 + k * 0.05), 0, 0.12), (sx * 0.3, 0, 1), 0.03, 0.16, seg=5)
        mb.tube([(0, 0, 0), (sx * 0.03, 0, -0.32)], [0.075, 0.065], armor, seg=10)
        mb.tube([(sx * 0.03, 0, -0.32), (sx * 0.03, -0.18, -0.55)], [0.065, 0.06], armor, seg=10)
        mb.add('sphere', trim, loc=(sx * 0.03, 0, -0.32), scale=(0.075, 0.075, 0.075))
        hand = Vector((sx * 0.03, -0.2, -0.6))
        mb.add('sphere', armor, loc=tuple(hand), scale=(0.06, 0.06, 0.07))
        if side == "R":
            d = Vector((sx * 0.3, -0.55, 0.78)).normalized()
            rot = tuple(Vector((0, 0, 1)).rotation_difference(d).to_euler())
            mb.add('cube', blade, loc=tuple(hand + d * 0.62), rot=rot, scale=(0.09, 0.018, 1.0))
            cone_to(mb, blade, hand + d * 1.12, d, 0.06, 0.14, seg=4)
            mb.add('cube', trim, loc=tuple(hand + d * 0.1), rot=rot, scale=(0.3, 0.05, 0.04))
            mb.tube([hand - d * 0.12, hand + d * 0.08], [0.02, 0.02], mat("Grip", (0.25, 0.15, 0.08), 0.8), seg=6)
        else:
            c = hand + Vector((sx * 0.08, -0.03, 0.05))
            sh_rot = (0, sx * math.pi / 2, -sx * 0.6)
            q = Euler(sh_rot).to_matrix()
            verts = []
            for (u, v) in ((0, 0.32), (0.2, 0.2), (0.17, -0.12), (0, -0.4), (-0.17, -0.12), (-0.2, 0.2)):
                verts.append(tuple(c + q @ Vector((u, v, 0))))
            mb.poly(verts, [(0, 1, 2, 3, 4, 5)], armor)
            mb.poly(list(reversed(verts)), [(0, 1, 2, 3, 4, 5)], armor)
            ring = [c + q @ Vector((u * 1.03, v * 1.03, 0.01)) for (u, v) in ((0, 0.32), (0.2, 0.2), (0.17, -0.12), (0, -0.4), (-0.17, -0.12), (-0.2, 0.2), (0, 0.32))]
            mb.tube(ring, [0.02] * len(ring), trim, seg=5)
            mb.add('sphere', eyeg, loc=tuple(c + q @ Vector((0, 0, 0.03))), scale=(0.06, 0.06, 0.06))
        mb.build(f"Mon_DarkKnight_Arm{side}", COLL, loc=(sx * 0.3, 0, 1.6), parent=body)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.tube([(0, 0, 0), (0, 0, -0.45)], [0.09, 0.075], armor, seg=10)
        mb.add('sphere', trim, loc=(0, -0.04, -0.47), scale=(0.085, 0.07, 0.08))
        mb.tube([(0, 0, -0.48), (0, 0.0, -0.9)], [0.075, 0.065], armor, seg=10)
        mb.add('sphere', armor, loc=(0, -0.07, -0.93), scale=(0.075, 0.16, 0.05))
        mb.build(f"Mon_DarkKnight_Leg{side}", COLL, loc=(sx * 0.12, 0, 0.96), parent=r)


# ------------------------------------------------------------------ デビルアイ
def build_evileye(x):
    r = root("Mon_EvilEye", x)
    flesh = mat("EyeFlesh", (0.42, 0.12, 0.32), 0.5)
    vein = mat("EyeVein", (0.7, 0.1, 0.22), 0.6)
    iris = mat("EyeIrisRed", (1.0, 0.15, 0.2), 0.2, emit=(1.0, 0.1, 0.15), emit_strength=3.0)
    wing = mat("EyeWing", (0.22, 0.08, 0.25), 0.7, double=True)
    body, me = meta_part("Mon_EvilEye_Body", [E_ball((0, 0, 0), 0.5), E_ell((0, 0.1, 0.05), 0.45, 0.4, 0.45)], [flesh], res=0.012, faces=4000, parent=r, loc=(0, 0, 1.6))
    mb = CMB()
    mb.add('sphere', M_EYEW, loc=(0, -0.24, 0.0), scale=(0.36, 0.3, 0.36))
    mb.add('sphere', iris, loc=(0, -0.48, 0.0), scale=(0.19, 0.08, 0.19))
    mb.add('sphere', M_PUPIL, loc=(0, -0.54, 0.0), scale=(0.05, 0.04, 0.15))
    mb.add('sphere', M_EYEW, loc=(0.06, -0.55, 0.08), scale=(0.035, 0.02, 0.035))
    # まぶた（半目）
    mb.add('sphere', flesh, loc=(0, -0.2, 0.2), rot=(0.3, 0, 0), scale=(0.42, 0.34, 0.22))
    mb.add('sphere', flesh, loc=(0, -0.22, -0.24), rot=(-0.2, 0, 0), scale=(0.4, 0.32, 0.17))
    rng = random.Random(3)
    for k in range(8):
        a_ = rng.uniform(0, math.tau)
        pts = [Vector((math.sin(a_) * 0.3 * t + rng.uniform(-0.02, 0.02), -0.4 + 0.1 * t, math.cos(a_) * 0.3 * t)) for t in [j / 3 for j in range(4)]]
        mb.tube(pts, [0.008] * 4, vein, seg=4)
    for k in range(6):
        a_ = k / 6 * math.pi - math.pi / 2
        cone_to(mb, vein, (math.sin(a_) * 0.35, 0.15, math.cos(a_) * 0.35 + 0.15), (math.sin(a_), 0.6, math.cos(a_) + 0.5), 0.06, 0.25, seg=5)
    mb.build("Mon_EvilEye_Parts", COLL, parent=body)
    mb = CMB()
    for k in range(5):
        a_ = k / 5 * math.tau
        pts = []
        for j in range(7):
            t = j / 6
            pts.append(Vector((math.cos(a_) * (0.2 + 0.1 * t) + math.sin(t * 4 + k) * 0.08 * t, math.sin(a_) * (0.2 + 0.1 * t), -0.3 - t * 0.85)))
        mb.tube(pts, [0.07 * (1 - t * 0.8) for t in [j / 6 for j in range(7)]], flesh, seg=8)
    mb.build("Mon_EvilEye_Tentacles", COLL, loc=(0, 0, 1.6), parent=r)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        bat_wing(mb, sx, 0.75, flesh, wing, seed=sx + 3)
        mb.build(f"Mon_EvilEye_Wing{side}", COLL, loc=(sx * 0.4, 0.12, 1.75), parent=r)


# ------------------------------------------------------------------ 混沌王ゼノス（最後のボス）
def build_zenos(x):
    r = root("Mon_Zenos", x)
    robe = mat("ZenosRobe", (0.1, 0.06, 0.14), 0.8, double=True)
    armor = mat("ZenosArmor", (0.2, 0.18, 0.27), 0.35, 0.7)
    gold = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
    skin = mat("ZenosSkin", (0.36, 0.4, 0.52), 0.5)
    gem = mat("ZenosGem", (0.9, 0.2, 1.0), 0.1, emit=(0.85, 0.15, 1.0), emit_strength=8.0)
    eyeg = mat("ZenosEye", (1.0, 0.35, 0.9), 0.2, emit=(1.0, 0.3, 0.9), emit_strength=8.0)
    hornm = mat("ZenosHorn", (0.12, 0.1, 0.14), 0.4)
    memb = mat("ZenosWing", (0.18, 0.05, 0.25), 0.75, double=True)
    # 胴（鎧）
    el = [E_ell((0, 0, 2.65), 0.55, 0.35, 0.45), E_ell((0, -0.02, 2.2), 0.42, 0.3, 0.32), E_ell((0, 0, 1.9), 0.38, 0.28, 0.22),
          E_cap((0, 0, 2.95), (0, -0.04, 3.2), 0.18)]
    for s in (-1, 1):
        el.append(E_ell((s * 0.24, -0.2, 2.72), 0.22, 0.1, 0.2))
    body, me = meta_part("Mon_Zenos_Body", el, [armor], res=0.016, faces=7000, parent=r)
    surf = Surface(me)
    mb = CMB()
    # 裾の広がったローブ（ギザギザの裾）
    seg = 36
    rings = [(1.95, 0.42), (1.4, 0.62), (0.8, 0.85), (0.2, 1.08)]
    verts, faces = [], []
    rng = random.Random(6)
    for ri, (z, rr) in enumerate(rings):
        for k in range(seg):
            a_ = k / seg * math.tau
            jag = (rng.uniform(-0.18, 0.05) if ri == len(rings) - 1 else 0)
            verts.append((math.sin(a_) * rr, -math.cos(a_) * rr * 0.85, z + jag))
    for ri in range(len(rings) - 1):
        for k in range(seg):
            a_ = ri * seg + k
            b_ = ri * seg + (k + 1) % seg
            faces.append((a_, b_, b_ + seg, a_ + seg))
    mb.poly(verts, faces, robe, smooth=True)
    mb.add('cyl', gold, loc=(0, 0, 1.92), r1=0.44, r2=0.43, depth=0.1, seg=28, scale=(1, 0.85, 1))
    p, n = surf_point(surf, 0, 2.6)
    if p:
        mb.add('ico', gem, loc=p + n * 0.05, r=0.13, sub=2)
        mb.add('cyl', gold, loc=p + n * 0.01, rot=tuple(basis_euler(n)), r1=0.19, r2=0.19, depth=0.05, seg=20, scale=(1, 1, 1))
    for s in (-1, 1):
        mb.add('sphere', armor, loc=(s * 0.62, 0, 2.95), scale=(0.32, 0.3, 0.2))
        mb.add('cyl', gold, loc=(s * 0.62, 0, 2.88), r1=0.31, r2=0.31, depth=0.04, seg=20)
        for k in range(3):
            cone_to(mb, hornm, (s * (0.5 + k * 0.12), 0, 3.08), (s * 0.4, 0, 1), 0.05, 0.35 - k * 0.06, seg=6)
    mb.build("Mon_Zenos_Robe", COLL, parent=body)
    hel = [E_ell((0, 0, 0.14), 0.17, 0.19, 0.19), E_ell((0, -0.1, 0.05), 0.13, 0.11, 0.12), E_ell((0, -0.12, -0.06), 0.1, 0.09, 0.06)]
    head, hme = meta_part("Mon_Zenos_Head", hel, [skin], res=0.006, faces=3500, parent=body, loc=(0, -0.04, 3.28))
    hs = Surface(hme)
    mb = CMB()
    for s in (-1, 1):
        p, n = hs.ray(Vector((s * 0.06, -1, 0.1)), Vector((0, 1, 0)))
        if p:
            mb.add('sphere', eyeg, loc=p - n * 0.003, rot=basis_euler(n), scale=(0.035, 0.012, 0.016))
        mb.tube([(s * 0.12, 0.0, 0.25), (s * 0.3, 0.08, 0.45), (s * 0.34, 0.25, 0.7), (s * 0.25, 0.4, 0.86)], [0.06, 0.045, 0.025, 0.004], hornm, seg=10)
        mb.tube([(s * 0.08, -0.05, 0.3), (s * 0.14, 0.0, 0.5), (s * 0.12, 0.1, 0.62)], [0.03, 0.02, 0.003], hornm, seg=8)
    # 冠
    for k in range(7):
        a_ = (k - 3) * 0.3
        cone_to(mb, gold, (math.sin(a_) * 0.17, -math.cos(a_) * 0.16, 0.26), (math.sin(a_) * 0.3, -0.3, 1), 0.025, 0.14 + (0.06 if k == 3 else 0), seg=4)
    mb.add('cyl', gold, loc=(0, 0, 0.25), r1=0.185, r2=0.18, depth=0.05, seg=24, scale=(1, 1.05, 1))
    mb.add('ico', gem, loc=(0, -0.18, 0.28), r=0.035, sub=1)
    mb.build("Mon_Zenos_Crown", COLL, parent=head)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        mb.tube([(0, 0, 0), (sx * 0.12, -0.05, -0.55)], [0.13, 0.11], armor, seg=12)
        mb.tube([(sx * 0.12, -0.05, -0.55), (sx * 0.08, -0.4, -0.95)], [0.11, 0.09], armor, seg=12)
        mb.add('cyl', gold, loc=(sx * 0.1, -0.24, -0.76), rot=(0.75, 0, 0), r1=0.12, r2=0.11, depth=0.18, seg=16)
        hand = Vector((sx * 0.07, -0.45, -1.02))
        mb.add('sphere', skin, loc=tuple(hand), scale=(0.09, 0.09, 0.1))
        for k in (-1, 0, 1):
            cone_to(mb, hornm, hand + Vector((k * 0.04, -0.05, -0.05)), (k * 0.3, -1, -0.5), 0.02, 0.14)
        if side == "R":
            mb.tube([hand + Vector((0, 0, -1.7)), hand + Vector((0, 0, 0.9))], [0.035, 0.035], hornm, seg=8)
            top = hand + Vector((0, 0, 0.9))
            for k in range(4):
                a_ = k / 4 * math.tau
                mb.tube([top, top + Vector((math.cos(a_) * 0.15, math.sin(a_) * 0.15, 0.15)), top + Vector((math.cos(a_) * 0.08, math.sin(a_) * 0.08, 0.35))], [0.02, 0.015, 0.004], gold, seg=6)
            mb.add('ico', gem, loc=tuple(top + Vector((0, 0, 0.2))), r=0.12, sub=2)
        mb.build(f"Mon_Zenos_Arm{side}", COLL, loc=(sx * 0.78, 0, 2.95), parent=body)
    for side, sx in (("L", 1), ("R", -1)):
        mb = CMB()
        bat_wing(mb, sx, 2.6, armor, memb, claw_m=hornm, tatter=1.0, seed=sx + 11)
        mb.build(f"Mon_Zenos_Wing{side}", COLL, loc=(sx * 0.35, 0.32, 3.0), parent=r)


build_scorpion(44.0)
build_mummy(48.0)
build_cactus(51.0)
build_anubis(54.0)
build_snowman(58.0)
build_penguin(61.0)
build_yeti(64.0)
build_lizard(69.0)
build_firebird(73.0)
build_ifrit(77.0)
build_darkknight(82.0)
build_evileye(86.0)
build_zenos(92.0)
print("sequel monsters done")
