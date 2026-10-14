"""
建物・ダンジョン用の PBR テクスチャ（つなぎ目なしでくり返せる）を生成する。

  python scripts/gen_textures.py

出力：public/assets/tex/<種類>_a.jpg（色）, _n.jpg（法線）, _m.jpg（R=AO, G=粗さ, B=高さ）
     同じものを 512px にした public/assets/tex/lo/ も作る（軽量設定用）

色は「平均の明るさ 0.5」にそろえてあり、ゲーム側でマテリアルの色に掛け合わせる
（色の指定は Blender のマテリアルのまま、模様と凹凸だけをテクスチャが受け持つ）。
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

N = 1024
OUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'assets', 'tex')


# ---------------------------------------------------------------- 基本の道具（すべて周期的＝タイル可能）
def rng(seed):
    return np.random.default_rng(seed)


def blur(a, s):
    return ndimage.gaussian_filter(a, s, mode='wrap')


def noise(r, scale, n=N):
    """ガウスでぼかした白色雑音（scale ピクセルくらいの粒）。-1..1 付近に正規化"""
    a = blur(r.standard_normal((n, n)), scale)
    return a / (a.std() * 3 + 1e-9)


def fbm(r, base, octaves=5, gain=0.5, n=N):
    out = np.zeros((n, n))
    amp, s, tot = 1.0, base, 0.0
    for _ in range(octaves):
        out += noise(r, max(s, 0.6), n) * amp
        tot += amp
        amp *= gain
        s /= 2
    return out / tot


def aniso_noise(r, sx, sy, n=N):
    a = ndimage.gaussian_filter(r.standard_normal((n, n)), (sy, sx), mode='wrap')
    return a / (a.std() * 3 + 1e-9)


def voronoi(r, count, n=N, jitter=1.0):
    """周期的なボロノイ：F1, F2, 最寄りのセル番号"""
    g = int(np.sqrt(count))
    pts = []
    for j in range(g):
        for i in range(g):
            pts.append(((i + 0.5 + (r.random() - 0.5) * jitter) / g, (j + 0.5 + (r.random() - 0.5) * jitter) / g))
    pts = np.mod(np.array(pts), 1.0)
    tree = cKDTree(pts, boxsize=1.0)
    yy, xx = np.mgrid[0:n, 0:n] / n
    q = np.stack([xx.ravel(), yy.ravel()], 1)
    d, idx = tree.query(q, k=2)
    return d[:, 0].reshape(n, n) * g, d[:, 1].reshape(n, n) * g, idx[:, 0].reshape(n, n), len(pts)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def normal_from_height(h, strength):
    """高さ（0..1、1 ピクセル = 1/N タイル）→ 接空間法線（OpenGL 流儀：+Y が上＝v の増える向き）"""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    drow = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx = -dx * strength
    ny = drow * strength          # 画像の行は下向き、v は上向き
    nz = np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / ln, ny / ln, nz / ln], -1)


def cavity_ao(h, radii=(2, 6, 18), depth=4.0):
    ao = np.ones_like(h)
    for rr in radii:
        d = np.clip(blur(h, rr) - h, 0, None)
        ao *= 1 - np.clip(d * depth, 0, 0.6)
    return ao


def hsv_tint(base, var, r_amt=0.0, g_amt=0.0, b_amt=0.0):
    return np.stack([base * (1 + var * r_amt), base * (1 + var * g_amt), base * (1 + var * b_amt)], -1)


def save(name, alb, nrm, ao, rough, height):
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, 'lo'), exist_ok=True)
    # 色：平均の明るさを 0.5 に（ゲームでマテリアル色 × 2 を掛ける）
    alb = np.clip(alb, 0, None)
    lum = (alb[..., 0] * 0.2126 + alb[..., 1] * 0.7152 + alb[..., 2] * 0.0722).mean()
    alb = np.clip(alb * (0.5 / lum), 0, 1)
    a8 = (np.power(alb, 1 / 2.2) * 255 + 0.5).astype(np.uint8)        # sRGB で保存
    n8 = ((nrm * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)
    hh = (height - height.min()) / (np.ptp(height) + 1e-9)
    m8 = (np.stack([np.clip(ao, 0, 1), np.clip(rough, 0, 1), hh], -1) * 255 + 0.5).astype(np.uint8)
    for suf, arr in (('a', a8), ('n', n8), ('m', m8)):
        im = Image.fromarray(arr, 'RGB')
        im.save(os.path.join(OUT, f'{name}_{suf}.jpg'), quality=93, subsampling=0)
        im.resize((N // 2, N // 2), Image.LANCZOS).save(os.path.join(OUT, 'lo', f'{name}_{suf}.jpg'), quality=90, subsampling=0)
    print('wrote', name)


yy, xx = np.mgrid[0:N, 0:N] / N     # 0..1 のタイル座標（yy は下向き）


# ---------------------------------------------------------------- 石積み（城・家の土台・塔）  タイル = 3.6m
def stone():
    r = rng(11)
    # 段の高さをばらばらに（合計 1.0）
    hs = [r.uniform(0.7, 1.3) for _ in range(7)]
    tot = sum(hs)
    edges = np.cumsum([0] + [h / tot for h in hs])
    rows = len(hs)
    wy = yy + fbm(r, 120, 2) * 0.004
    row = np.clip(np.searchsorted(edges, wy, side='right') - 1, 0, rows - 1)
    rh = (edges[1:] - edges[:-1])[row]
    fy = (wy - edges[row]) / rh
    bx = np.zeros((N, N))
    bw = np.ones((N, N))
    bid = np.zeros((N, N), int)
    for k in range(rows):
        cuts = [0.0]
        while cuts[-1] < 1.0:
            cuts.append(cuts[-1] + r.uniform(0.09, 0.3))
        sc = 1.0 / cuts[-1]
        cuts = np.array([c * sc for c in cuts])
        off = r.random()
        m = row == k
        u = np.mod(xx[m] + off + fbm(r, 80, 2)[m] * 0.003, 1.0)
        i_ = np.searchsorted(cuts, u, side='right') - 1
        bx[m] = (u - cuts[i_]) / (cuts[i_ + 1] - cuts[i_])
        bw[m] = (cuts[i_ + 1] - cuts[i_])
        bid[m] = k * 100 + i_
    dxe = np.minimum(bx, 1 - bx) * bw
    dye = np.minimum(fy, 1 - fy) * rh
    # 角は丸く、ふちは欠けて不規則に
    jag = fbm(r, 5, 4) * 0.005 + fbm(r, 20, 3) * 0.004
    d = np.sqrt(np.minimum(dxe, 0.03) ** 2 + np.minimum(dye, 0.03) ** 2) * 0 + np.minimum(dxe, dye) + jag
    mortar = 0.004
    edge = smooth(mortar, mortar + 0.022, d)
    ids = np.unique(bid)
    look = lambda tbl: np.vectorize(tbl.get)(bid)
    vh = look({i: r.uniform(-0.3, 0.3) for i in ids})
    tx = look({i: r.uniform(-1, 1) for i in ids})
    ty = look({i: r.uniform(-1, 1) for i in ids})
    cv = look({i: r.uniform(-1, 1) for i in ids})
    cw = look({i: r.uniform(-1, 1) for i in ids})
    surf = fbm(r, 22, 6) * 0.5 + noise(r, 1.5) * 0.1 + (1 - np.abs(fbm(r, 9, 3)) * 2) * 0.1
    h = edge * (0.75 + vh * 0.1 + tx * (bx - 0.5) * 0.06 + ty * (fy - 0.5) * 0.04 + surf * 0.2)
    h = np.where(d < mortar, 0.18 + noise(r, 1.2) * 0.03, h)
    base = 0.5 + cv * 0.09 + fbm(r, 30, 4) * 0.09 + noise(r, 2.5) * 0.05
    alb = hsv_tint(base, cw, 0.08, 0.02, -0.06)
    mort = np.stack([0.42 + noise(r, 1.5) * 0.03] * 3, -1) * np.array([1.0, 0.97, 0.9])
    k_ = (1 - edge)[..., None]
    alb = alb * (1 - k_) + mort * k_
    # 雨だれ・苔
    streak = smooth(0.2, 0.8, aniso_noise(r, 4, 160) + 0.2) * smooth(0.3, 0.7, fbm(r, 90, 3))
    alb *= (1 - streak * 0.18)[..., None]
    lichen = smooth(0.58, 0.82, fbm(r, 25, 5)) * edge
    alb = alb * (1 - lichen[..., None] * 0.3) + lichen[..., None] * np.array([0.42, 0.45, 0.3]) * 0.3
    ao = cavity_ao(h, (2, 6, 16), depth=3.0)
    rough = 0.82 + (1 - edge) * 0.12 - lichen * 0.05
    save('stone', alb, normal_from_height(h, 8.0), ao ** 0.6, rough, h)


# ---------------------------------------------------------------- 瓦屋根（丸みのある洋瓦が重なる）  タイル = 2.0m（9 段 × 10 列）
def roof():
    r = rng(23)
    rows, cols = 9, 10
    v = (1 - yy) * rows                 # 上に行くほど増える（屋根の上り）
    rw = np.floor(v).astype(int)
    fv = v - rw                         # 0 = 瓦の下端, 1 = 上端（上の段の下にもぐる）
    u = xx * cols + (rw % 2) * 0.5
    cl = np.floor(u).astype(int) % cols
    fu = u - np.floor(u)
    key = rw * 31 + cl
    ks = np.unique(key)
    jv = np.vectorize({k: r.uniform(-1, 1) for k in ks}.get)(key)
    tv = np.vectorize({k: r.uniform(-1, 1) for k in ks}.get)(key)
    sk = np.vectorize({k: r.uniform(-1, 1) for k in ks}.get)(key)
    fu2 = np.clip(fu + sk * 0.03 * (fv - 0.5), 0, 1)
    # 断面：かまぼこ形（中央が高い）。下端がいちばん前に出て、上へ行くほど上の段の下にもぐる
    arc = np.sqrt(np.clip(1 - (2 * fu2 - 1) ** 2, 0, 1))
    slope = 0.55 + 0.45 * (1 - fv)
    side = smooth(0.0, 0.05, fu2) * smooth(1.0, 0.95, fu2)
    lip = smooth(0.0, 0.07, fv)
    h = (0.25 + 0.55 * arc) * slope * lip + jv * 0.02
    h += fbm(r, 6, 4) * 0.025
    # 下端のすぐ下（次の段の上部）に落ちる影
    shadow = 1 - (1 - smooth(0.0, 0.25, fv)) * 0.0
    base = 0.5 + tv * 0.09 + fbm(r, 40, 4) * 0.07 + noise(r, 1.5) * 0.02
    alb = hsv_tint(base, tv, 0.06, -0.02, -0.08)
    weather = smooth(0.35, 0.75, fbm(r, 50, 5))
    alb *= (1 - weather * 0.2)[..., None]
    moss = smooth(0.6, 0.8, fbm(r, 20, 5)) * (1 - arc * 0.6) * smooth(0.6, 0.0, fv)
    alb = alb * (1 - moss[..., None] * 0.55) + moss[..., None] * np.array([0.3, 0.36, 0.18]) * 0.55
    # 瓦のすき間（谷）と、上の段に隠れる部分は暗い
    alb *= (0.45 + 0.55 * arc ** 0.5)[..., None] * (0.6 + 0.4 * lip)[..., None] * (0.75 + 0.25 * slope)[..., None]
    ao = cavity_ao(h, (2, 6, 14), depth=3.5) * (0.55 + 0.45 * arc ** 0.4)
    rough = 0.55 + (1 - arc) * 0.2 + weather * 0.15 + moss * 0.15
    save('roof', alb, normal_from_height(h, 10.0), ao, rough, h)


# ---------------------------------------------------------------- 木材（柱・梁・扉）  タイル = 1.0m、木目は縦
def wood():
    r = rng(37)
    planks = 4
    warp = aniso_noise(r, 30, 300) * 0.25 + aniso_noise(r, 8, 120) * 0.05
    px = xx * planks
    pid = np.floor(px).astype(int)
    pf = px - pid
    seam = smooth(0.0, 0.015, pf) * smooth(1.0, 0.985, pf)
    off = np.array([r.random() * 10 for _ in range(planks)])[pid]
    tint = np.array([r.uniform(-1, 1) for _ in range(planks)])[pid]
    # 年輪：板の中で縦に走る細い筋（うねりは弱く）
    g = (pf + warp + off) * 9
    rings = np.abs(np.sin(g * np.pi)) ** 0.35
    fiber = aniso_noise(r, 0.7, 90) * 0.5 + aniso_noise(r, 0.4, 25) * 0.3 + aniso_noise(r, 2, 200) * 0.4
    base = 0.5 + rings * 0.1 + fiber * 0.12 + tint * 0.07
    alb = hsv_tint(base, rings - 0.5 + tint * 0.5, 0.06, 0.0, -0.1)
    h = 0.6 + rings * 0.04 + fiber * 0.09
    h = h * (0.3 + 0.7 * seam)
    for _ in range(4):
        cx, cy = r.random(), r.random()
        dd = np.sqrt((((xx - cx + 0.5) % 1) - 0.5) ** 2 * 16 + (((yy - cy + 0.5) % 1) - 0.5) ** 2)
        k = smooth(0.03, 0.0, dd)
        alb *= (1 - k * 0.55)[..., None]
        h -= k * 0.06
    alb *= (0.45 + 0.55 * seam)[..., None]
    ao = cavity_ao(h, (2, 6), depth=3.0)
    rough = 0.72 + fiber * 0.1 + (1 - seam) * 0.2
    save('wood', alb, normal_from_height(h, 6.0), ao, rough, h)


# ---------------------------------------------------------------- 床板  タイル = 2.0m（8 枚）
def planks():
    r = rng(41)
    boards = 8
    py = yy * boards
    row = np.floor(py).astype(int)
    fy = py - row
    h = np.zeros((N, N))
    lens = {}
    bx = np.zeros((N, N))
    bidx = np.zeros((N, N), int)
    for k in range(boards):
        cuts = [0.0]
        while cuts[-1] < 1.0:
            cuts.append(cuts[-1] + r.uniform(0.35, 0.8))
        sc = 1.0 / cuts[-1]
        cuts = np.array([c * sc for c in cuts])
        off = r.random()
        m = row == k
        uu = np.mod(xx[m] + off, 1.0)
        i = np.searchsorted(cuts, uu, side='right') - 1
        bx[m] = (uu - cuts[i]) / (cuts[i + 1] - cuts[i])
        bidx[m] = k * 50 + i
        lens[k] = cuts
    seam_y = smooth(0.0, 0.03, fy) * smooth(1.0, 0.97, fy)
    seam_x = smooth(0.0, 0.006, bx) * smooth(1.0, 0.994, bx)
    seam = seam_y * seam_x
    ids = np.unique(bidx)
    tint = np.vectorize({i: r.uniform(-1, 1) for i in ids}.get)(bidx)
    tilt = np.vectorize({i: r.uniform(-1, 1) for i in ids}.get)(bidx)
    grain = aniso_noise(r, 90, 1.2) * 0.6 + aniso_noise(r, 30, 0.6) * 0.4
    rings = np.sin((yy * boards * 3 + grain * 2 + tint) * np.pi * 2) * 0.5 + 0.5
    base = 0.5 + tint * 0.1 + grain * 0.12 + rings * 0.05
    alb = hsv_tint(base, tint, 0.06, 0.0, -0.08)
    wear = smooth(0.3, 0.7, fbm(r, 80, 4))
    alb *= (1 - wear * 0.15)[..., None]
    h = (0.7 + grain * 0.06 + tilt * (fy - 0.5) * 0.04) * (0.25 + 0.75 * seam)
    # 釘
    for k in range(boards):
        for c in lens[k][:-1]:
            for dy in (0.25, 0.75):
                pass
    alb *= (0.45 + 0.55 * seam)[..., None]
    ao = cavity_ao(h, (2, 8), depth=3.0)
    rough = 0.65 + wear * 0.2 + (1 - seam) * 0.2
    save('planks', alb, normal_from_height(h, 6.0), ao, rough, h)


# ---------------------------------------------------------------- しっくい壁  タイル = 2.5m
def plaster():
    r = rng(53)
    lump = fbm(r, 40, 6) * 0.7 + fbm(r, 8, 4) * 0.35 + noise(r, 1.2) * 0.06
    trowel = aniso_noise(r, 60, 10) * 0.35 + aniso_noise(r, 20, 4) * 0.15
    h = 0.6 + lump * 0.3 + trowel * 0.2
    # はがれて下地のれんがが見えるところ（ところどころ）
    peel = smooth(0.56, 0.62, fbm(r, 90, 5) + lump * 0.12)
    brow = 14
    by = yy * brow
    brw = np.floor(by).astype(int)
    bxx = xx * 7 + (brw % 2) * 0.5
    bf = np.minimum(np.minimum(by - brw, 1 - (by - brw)) * 1.0, np.minimum(bxx % 1, 1 - bxx % 1) * 0.5)
    bricks = smooth(0.02, 0.1, bf)
    rim = smooth(0.0, 0.03, peel) * (1 - smooth(0.6, 1.0, peel))
    h = h * (1 - peel) + peel * (0.2 + bricks * 0.2) + rim * 0.05
    # ひび
    c1, c2, _, _ = voronoi(rng(54), 25)
    crack = (1 - smooth(0.0, 0.02, c2 - c1)) * smooth(0.55, 0.75, fbm(r, 50, 4))
    h -= crack * 0.1
    base = 0.5 + lump * 0.07 + noise(r, 1.5) * 0.02
    alb = np.stack([base, base * 0.985, base * 0.95], -1)
    bt = fbm(r, 4, 2)
    under = np.stack([0.5 + bt * 0.1, 0.33 + bt * 0.06, 0.26 + bt * 0.05], -1) * (0.5 + 0.5 * bricks)[..., None]
    alb = alb * (1 - peel[..., None]) + under * peel[..., None]
    # 雨だれの縦すじ・下のほうの汚れ
    drip = smooth(0.3, 0.9, aniso_noise(r, 6, 140) + 0.3) * 0.5
    stain = smooth(0.45, 0.85, fbm(r, 60, 5) + yy * 0.35)
    alb = alb * (1 - (stain * 0.14 + drip * 0.08)[..., None])
    alb *= (1 - crack * 0.45)[..., None]
    ao = cavity_ao(h, (3, 10), depth=3.0)
    rough = 0.9 - stain * 0.05
    save('plaster', alb, normal_from_height(h, 9.0), ao, rough, h)


# ---------------------------------------------------------------- 洞窟の岩  タイル = 5.0m
def rock():
    r = rng(67)
    wx = fbm(r, 90, 3) * 0.12
    wy = fbm(r, 90, 3) * 0.12
    def warped(a):
        ix = (np.mgrid[0:N, 0:N][1] + wx * N).astype(int) % N
        iy = (np.mgrid[0:N, 0:N][0] + wy * N).astype(int) % N
        return a[iy, ix]
    ridge = warped(1 - np.abs(fbm(r, 70, 6)) * 2.2)
    ridge2 = warped(1 - np.abs(fbm(r, 25, 5)) * 2.0)
    strata = np.sin((yy + wy * 1.5 + fbm(r, 100, 2) * 0.1) * np.pi * 2 * 7) * 0.5 + 0.5
    c1, c2, _, _ = voronoi(r, 16, jitter=1.0)
    crack = warped((1 - smooth(0.0, 0.03, c2 - c1)) * smooth(0.45, 0.7, fbm(r, 60, 4)))
    h = 0.5 + ridge * 0.35 + ridge2 * 0.15 + fbm(r, 6, 5) * 0.1 + strata * 0.06 - crack * 0.25
    base = 0.5 + fbm(r, 50, 4) * 0.14 + strata * 0.06 + noise(r, 2) * 0.05 + ridge * 0.05
    alb = hsv_tint(base, strata - 0.5, 0.05, 0.0, -0.05)
    alb *= (1 - crack * 0.6)[..., None]
    ao = cavity_ao(h, (3, 10, 30), depth=2.5)
    rough = 0.85 + crack * 0.1
    save('rock', alb, normal_from_height(h, 8.0), ao, rough, h)


# ---------------------------------------------------------------- 布（じゅうたん）  タイル = 0.6m
def fabric():
    r = rng(71)
    t = 96
    wx = np.sin(xx * np.pi * 2 * t) * 0.5 + 0.5
    wy = np.sin(yy * np.pi * 2 * t) * 0.5 + 0.5
    over = (np.floor(xx * t) + np.floor(yy * t)) % 2
    weave = np.where(over > 0, wx * 0.7 + 0.3, wy * 0.7 + 0.3)
    fuzz = noise(r, 1.0) * 0.3 + fbm(r, 30, 4) * 0.3
    h = 0.5 + weave * 0.2 + fuzz * 0.15
    base = 0.5 + fuzz * 0.12 + weave * 0.05
    alb = np.stack([base, base, base], -1)
    ao = cavity_ao(h, (1, 4), depth=2.0)
    rough = np.full((N, N), 1.0)
    save('fabric', alb, normal_from_height(h, 3.0), ao, rough, h)


# ---------------------------------------------------------------- 石だたみ（床）  タイル = 3.0m
def flagstone():
    r = rng(83)
    d1, d2, idx, n = voronoi(r, 64, jitter=0.9)
    gap = d2 - d1
    edge = smooth(0.02, 0.12, gap)
    tint = np.array([r.uniform(-1, 1) for _ in range(n)])[idx]
    tilt = np.array([r.uniform(-1, 1) for _ in range(n)])[idx]
    h = edge * (0.7 + tilt * 0.06 + fbm(r, 12, 5) * 0.12) + (1 - edge) * (0.15 + noise(r, 1.5) * 0.05)
    base = 0.5 + tint * 0.08 + fbm(r, 35, 4) * 0.08 + noise(r, 2) * 0.03
    alb = hsv_tint(base, tint, 0.05, 0.0, -0.05)
    dirt = 1 - smooth(0.0, 0.15, gap)
    alb *= (1 - dirt * 0.45)[..., None]
    worn = smooth(0.4, 0.8, fbm(r, 90, 4))
    ao = cavity_ao(h, (2, 8, 20), depth=3.0)
    rough = 0.8 - worn * 0.2 + dirt * 0.15
    save('flagstone', alb, normal_from_height(h, 8.0), ao, rough, h)


if __name__ == '__main__':
    for f in (stone, roof, wood, planks, plaster, rock, fabric, flagstone):
        f()


# ================================================================ キャラクター用（骨格の初期姿勢の座標で貼る）
# ---------------------------------------------------------------- 服の布（綾織り）  タイル = 0.12m
def cloth():
    r = rng(101)
    t = 64
    d = (xx + yy) * t                    # 綾目（斜めの畝）
    twill = np.sin(d * np.pi * 2) * 0.5 + 0.5
    wx = np.sin(xx * np.pi * 2 * t * 2) * 0.5 + 0.5
    fuzz = noise(r, 0.8) * 0.4 + fbm(r, 60, 3) * 0.3
    h = 0.5 + twill * 0.25 + wx * 0.08 + fuzz * 0.12
    base = 0.5 + twill * 0.06 + fuzz * 0.08 + fbm(r, 200, 3) * 0.06
    alb = np.stack([base, base, base], -1)
    ao = cavity_ao(h, (1, 3), depth=2.0)
    rough = np.full((N, N), 0.95) - twill * 0.05
    save('cloth', alb, normal_from_height(h, 2.5), ao, rough, h)


# ---------------------------------------------------------------- 革  タイル = 0.25m
def leather():
    r = rng(103)
    d1, d2, _, _ = voronoi(r, 900, jitter=1.0)
    pebble = smooth(0.0, 0.25, d2 - d1)
    crease = 1 - np.abs(aniso_noise(r, 30, 6)) * 3
    crease = smooth(0.75, 1.0, crease)
    h = 0.5 + pebble * 0.25 + fbm(r, 20, 4) * 0.1 - crease * 0.15
    base = 0.5 + fbm(r, 80, 4) * 0.1 + pebble * 0.04
    alb = np.stack([base, base * 0.98, base * 0.95], -1) * (1 - crease * 0.25)[..., None]
    worn = smooth(0.4, 0.8, fbm(r, 120, 3))
    ao = cavity_ao(h, (1, 4), depth=2.5)
    rough = 0.6 + (1 - pebble) * 0.15 - worn * 0.15
    save('leather', alb, normal_from_height(h, 4.0), ao, rough, h)


# ---------------------------------------------------------------- 金属（打ち出し・細かな傷）  タイル = 0.5m
def metal():
    r = rng(107)
    d1, d2, _, _ = voronoi(r, 196, jitter=1.0)
    dent = d1 ** 2 * 0.6
    scratch = np.zeros((N, N))
    for _ in range(140):
        x0, y0 = r.random() * N, r.random() * N
        a = r.uniform(0, np.pi)
        L = r.uniform(20, 160)
        for k in range(int(L)):
            xi = int(x0 + np.cos(a) * k) % N
            yi = int(y0 + np.sin(a) * k) % N
            scratch[yi, xi] = 1
    scratch = blur(scratch, 0.6)
    h = 0.6 - dent * 0.5 + fbm(r, 6, 3) * 0.02 - scratch * 0.1
    base = 0.5 + fbm(r, 100, 4) * 0.06 - scratch * 0.1
    alb = np.stack([base, base, base], -1)
    smudge = smooth(0.3, 0.8, fbm(r, 140, 4))
    ao = cavity_ao(h, (2, 8), depth=1.5)
    rough = 0.3 + smudge * 0.25 + scratch * 0.2
    save('metal', alb, normal_from_height(h, 3.0), ao, rough, h)


# ---------------------------------------------------------------- 髪（細い毛筋）  タイル = 0.1m、毛は縦（v）方向
def hairs():
    r = rng(109)
    strands = aniso_noise(r, 0.7, 50) * 0.6 + aniso_noise(r, 1.5, 120) * 0.4
    clump = aniso_noise(r, 8, 200)
    h = 0.5 + strands * 0.3 + clump * 0.2
    base = 0.5 + strands * 0.12 + clump * 0.1
    alb = np.stack([base, base, base], -1)
    ao = cavity_ao(h, (1, 3), depth=2.0)
    rough = 0.45 + strands * 0.1
    save('hair', alb, normal_from_height(h, 2.0), ao, rough, h)


# ---------------------------------------------------------------- 肌（ごく細かい凹凸）  タイル = 0.08m
def skin():
    r = rng(113)
    d1, d2, _, _ = voronoi(r, 2500, jitter=1.0)
    pores = smooth(0.0, 0.2, d1) - 1
    h = 0.5 + pores * 0.08 + fbm(r, 12, 4) * 0.08
    base = 0.5 + fbm(r, 60, 4) * 0.03
    alb = np.stack([base * 1.01, base, base * 0.99], -1)
    ao = cavity_ao(h, (1, 3), depth=1.0)
    rough = 0.55 - pores * 0.1 + fbm(r, 100, 3) * 0.05
    save('skin', alb, normal_from_height(h, 1.2), ao, rough, h)


if __name__ == '__main__' and 'chars' in __import__('sys').argv:
    for f in (cloth, leather, metal, hairs, skin):
        f()
