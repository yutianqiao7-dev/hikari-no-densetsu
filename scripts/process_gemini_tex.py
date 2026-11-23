# -*- coding: utf-8 -*-
"""
Gemini で描いた質感の絵（art/src/gemini/tex_*.jpg）を、ゲームのテクスチャにする。

  *_a.jpg  色（各色の平均を 0.5 にそろえる → ゲームでは場所・材質の色に ×2 してかける）
  *_n.jpg  凹凸（明るさを高さとみなして法線にする）
  *_m.jpg  R = くぼみの陰（AO）、G = 粗さ

つなぎ目：左右・上下のふちの差が大きいときだけ、半分ずらした絵と中央でまぜて消す。
葉の房（leaves.jpg）はマゼンタの背景を抜いて、2×2 の葉のアトラス（PNG）にする。
  python scripts/process_gemini_tex.py
"""
import os
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'art', 'src', 'gemini')
OUT = os.path.join(ROOT, 'public', 'assets', 'tex')
N = 1024

# 出力名: (元の絵, 凹凸の強さ, 陰の強さ, 粗さの基準)
JOBS = {
    # 建物（surfaces.js）
    'stone': ('tex_stone', 7.0, 1.0, 0.85),
    'plaster': ('tex_plaster', 4.0, 0.7, 0.9),
    'wood': ('tex_wood', 4.0, 0.7, 0.75),
    'planks': ('tex_planks', 5.0, 0.9, 0.7),
    'roof': ('tex_roof', 8.0, 1.0, 0.8),
    'rock': ('tex_rock', 8.0, 1.0, 0.9),
    'flagstone': ('tex_cobble', 8.0, 1.0, 0.85),
    'tiles': ('tex_tiles', 4.0, 0.6, 0.45),
    'fabric': ('tex_carpet', 2.5, 0.6, 0.95),
    # 地面（terrain.js）
    'g_grass': ('tex_grass', 3.0, 0.6, 0.95),
    'g_grass2': ('tex_grass2', 3.0, 0.6, 0.95),
    'g_dirt': ('tex_dirt', 4.0, 0.7, 0.95),
    'g_sand': ('tex_sand', 2.5, 0.5, 0.95),
    'g_snow': ('tex_snow', 3.0, 0.5, 0.8),
    'g_lava': ('tex_lava', 6.0, 0.9, 0.85),
    'bark': ('tex_bark', 6.0, 0.9, 0.9),
}


# 出力名: (大きなむらを取る強さ, 明るさの差の強さ, 色の差を残す割合)
OPT = {
    'plaster': (1.0, 0.45, 0.2),
    'fabric': (0.85, 0.45, 0.3),
    'tiles': (0.6, 0.8, 0.3),
    'g_grass': (1.0, 0.9, 0.25),
    'g_grass2': (1.0, 0.9, 0.25),
    'g_snow': (1.0, 0.8, 0.3),
    'g_sand': (1.0, 0.9, 0.3),
    'g_dirt': (1.0, 0.9, 0.3),
}


def load(name):
    im = Image.open(os.path.join(SRC, name + '.jpg')).convert('RGB')
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((N, N), Image.LANCZOS)
    # 光の量（リニア）で計算する
    return (np.asarray(im).astype(np.float32) / 255.0) ** 2.2


def seam_score(a):
    """ふちの差 ÷ となりあう画素の差（1 くらいならつなぎ目は目立たない）"""
    inner = np.mean(np.abs(a[:, 1:] - a[:, :-1])) + np.mean(np.abs(a[1:] - a[:-1]))
    edge = np.mean(np.abs(a[:, 0] - a[:, -1])) + np.mean(np.abs(a[0] - a[-1]))
    return edge / max(inner, 1e-6)


def make_tileable(a):
    """半分ずらした絵と、中央ほど元の絵・ふちほどずらした絵になるようにまぜる"""
    r = np.roll(np.roll(a, N // 2, 0), N // 2, 1)
    t = np.linspace(-1, 1, N)
    X, Y = np.meshgrid(t, t)
    d = np.maximum(np.abs(X), np.abs(Y))
    w = np.clip((0.92 - d) / 0.35, 0, 1)
    w = w * w * (3 - 2 * w)
    return a * w[..., None] + r * (1 - w[..., None])


def lum(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def blur(x, s):
    im = Image.fromarray(np.clip(x * 255, 0, 255).astype(np.uint8))
    # 端をまたいでぼかすため、3×3 に並べてからぼかして中央を切り出す
    big = Image.new('L', (N * 3, N * 3))
    for i in range(3):
        for j in range(3):
            big.paste(im, (i * N, j * N))
    big = big.filter(ImageFilter.GaussianBlur(s))
    return np.asarray(big.crop((N, N, 2 * N, 2 * N))).astype(np.float32) / 255.0


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def save(name, arr, q=92):
    im = Image.fromarray(np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8))
    im.save(os.path.join(OUT, name + '.jpg'), quality=q, subsampling=0)
    os.makedirs(os.path.join(OUT, 'lo'), exist_ok=True)
    im.resize((N // 2, N // 2), Image.LANCZOS).save(os.path.join(OUT, 'lo', name + '.jpg'), quality=90, subsampling=0)


def process(out, src, nstr, aostr, rough):
    a = load(src)
    sc = seam_score(a)
    if sc > 1.6:
        a = make_tileable(a)
    # 色：大きな明るさのむら（くり返しが目立つ）を取ってから、明るさの変化を主に、色の変化は少しだけ残す
    flat, contrast, chroma = OPT.get(out, (0.85, 1.0, 0.3))
    L = lum(a)
    low = blur(L, 40)
    a = a * ((np.mean(L) / np.maximum(low, 0.02)) ** flat)[..., None]
    mean = np.maximum(a.reshape(-1, 3).mean(0), 1e-3)
    ratio = a / mean
    lr = lum(a) / max(lum(mean[None, None, :])[0, 0], 1e-3)
    lr = 1.0 + (lr - 1.0) * contrast
    alb = 0.5 * (lr[..., None] + chroma * (ratio - (lum(a) / max(lum(mean[None, None, :])[0, 0], 1e-3))[..., None]))
    # 高さ：明るさ（細かいところ）
    h = lum(a) ** (1 / 2.2)
    h = h - blur(h, 24) * 0.85
    h = (h - h.min()) / max(h.max() - h.min(), 1e-6)
    hs = blur(h, 1.2)
    nrm = normal_from_height(hs, nstr)
    cav = np.clip(1.0 - (blur(hs, 6) - hs) * 3.0 * aostr, 0.35, 1.0)
    ao = cav ** 1.2
    rg = np.clip(rough - (hs - 0.5) * 0.15, 0.3, 1.0)
    m = np.stack([ao, rg, np.zeros_like(ao)], -1)
    save(out + '_a', np.clip(alb, 0, 1) ** (1 / 2.2))     # sRGB で保存（ゲームで読むとリニアで平均 0.5）
    save(out + '_n', nrm)
    save(out + '_m', m)
    print(f'{out:10s} <- {src:12s} seam {sc:.2f}{" (tiled)" if sc > 1.6 else ""}')


def leaves():
    im = Image.open(os.path.join(SRC, 'leaves.jpg')).convert('RGB')
    a = np.asarray(im).astype(np.float32) / 255.0
    # マゼンタ（赤と青が強く緑が弱い）を背景とみなす
    mag = np.clip(((np.minimum(a[..., 0], a[..., 2]) - a[..., 1]) - 0.25) / 0.25, 0, 1)
    alpha = 1.0 - mag
    # ふちのマゼンタのにじみを緑に寄せる
    rgb = a.copy()
    spill = np.clip(np.minimum(a[..., 0], a[..., 2]) - a[..., 1], 0, 1)
    rgb[..., 0] -= spill * 0.6
    rgb[..., 2] -= spill * 0.9
    H, W = alpha.shape
    tiles = []
    for (y0, y1) in ((0, H // 2), (H // 2, H)):
        for (x0, x1) in ((0, W // 2), (W // 2, W)):
            al = alpha[y0:y1, x0:x1]
            ys, xs = np.where(al > 0.5)
            cy, cx = (ys.min() + ys.max()) // 2, (xs.min() + xs.max()) // 2
            r = int(max(ys.max() - ys.min(), xs.max() - xs.min()) * 0.52)
            sub = np.concatenate([rgb[y0:y1, x0:x1], al[..., None]], -1)
            pad = np.zeros((sub.shape[0] + 2 * r, sub.shape[1] + 2 * r, 4), np.float32)
            pad[r:r + sub.shape[0], r:r + sub.shape[1]] = sub
            crop = pad[cy:cy + 2 * r, cx:cx + 2 * r]
            tiles.append(Image.fromarray(np.clip(crop * 255, 0, 255).astype(np.uint8), 'RGBA').resize((512, 512), Image.LANCZOS))
    atlas = Image.new('RGBA', (1024, 1024))
    for k, t in enumerate(tiles):
        atlas.paste(t, ((k % 2) * 512, (k // 2) * 512))
    atlas.save(os.path.join(OUT, 'leaves.png'))
    print('leaves.png (2x2)')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for out, (src, nstr, aostr, rough) in JOBS.items():
        process(out, src, nstr, aostr, rough)
    leaves()
