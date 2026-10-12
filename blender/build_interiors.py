# -*- coding: utf-8 -*-
"""
ひかりの伝説 — ダンジョン（ほこらの洞窟）と まおうの塔の内部（build_world.py の後に実行）

タイル配置図（1 マス 4m）から床・壁・装飾を自動生成する。
  #  壁        .  床         S  出口（フィールドへ）   U  上り階段   D  下り階段
  C  宝箱      T  かがり火    P  柱（塔）             W  水（洞窟）  R  じゅうたん（塔）
  B  ボスの位置 O  ひかりのオーブの祭壇
各フロアはゲーム座標 x=2000 以降の離れた場所に並べ、階段はフェードで移動する（DQ 方式）。
配置図・宝箱・かがり火などのデータはコレクション "Interiors" のカスタムプロパティに JSON で保存し、export_game.py が書き出す。
"""
import os, sys, math, random, json
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\OWNER-1121R\Desktop\クロード\ドラクエ\blender"
sys.path.insert(0, _here)
import importlib, bkit
importlib.reload(bkit)
from bkit import *
import bpy
from mathutils import Vector

CELL = 4.0

FLOORS = [
    ("cave1", "ほこらの洞窟 B1", "cave", [
        "####################",
        "#S...#####......C###",
        "#....#####.####.####",
        "#.T.........##..####",
        "###.#######.##.....#",
        "###.#######.######.#",
        "#C....###.....T##..#",
        "#.....###.###.###..#",
        "##.######.#C#....#.#",
        "##.######.#.####.#.#",
        "##....T.....####...#",
        "######.####.######.#",
        "#.....T.....#..D...#",
        "#.####.####.#..###.#",
        "#......C....#......#",
        "####################",
    ]),
    ("cave2", "ほこらの洞窟 B2", "cave", [
        "####################",
        "#U..##WWWW####...C.#",
        "#...##WWWW####.....#",
        "#.T...........##.T.#",
        "####.#######..##.###",
        "#C...#.....#..##.###",
        "#....#.WW..#.......#",
        "####.#.WW..#####.###",
        "####.......#####.###",
        "########.#######.###",
        "#..T.....#####.....#",
        "#.................T#",
        "#..WW....B.....WW..#",
        "#..WW..........WW..#",
        "#.T......O.......T.#",
        "####################",
    ]),
    ("tower1", "まおうの塔 1F", "tower", [
        "####################",
        "#T.P....#UU#....P.T#",
        "#.......#RR#.......#",
        "#..P....#RR#....P..#",
        "#.......#RR#.......#",
        "#C.P.....RR.....P.C#",
        "#........RR........#",
        "####.P...RR...P.####",
        "#.......RRRR.......#",
        "#..P....RRRR....P..#",
        "#.T.....RRRR.....T.#",
        "#.......RRRR.......#",
        "#.......RRRR.......#",
        "#........SS........#",
        "####################",
    ]),
    ("tower2", "まおうの塔 2F", "tower", [
        "####################",
        "#D....#.....#.....C#",
        "#.###.#.###.#.###..#",
        "#.#.T.#.#.#...#....#",
        "#.#####.#.#####.####",
        "#.......P...P......#",
        "######.#####.####..#",
        "#C.....#..T#.....#.#",
        "#.####.#.###.###.#.#",
        "#....#...#...#C#...#",
        "####.#####.###.###.#",
        "#T.........P.....#.#",
        "#.#######.#####.##.#",
        "#.........#.......U#",
        "####################",
    ]),
    ("tower3", "まおうの塔 3F", "tower", [
        "####################",
        "######...BB...######",
        "#P..P...RRRR...P..P#",
        "#.......RRRR.......#",
        "#T.P....RRRR....P.T#",
        "#.......RRRR.......#",
        "#..P....RRRR....P..#",
        "#.......RRRR.......#",
        "#.T.....RRRR.....T.#",
        "#........DD........#",
        "####################",
    ]),
]
SOLID = set("#W")


def validate(fid, grid):
    w = len(grid[0])
    for r, row in enumerate(grid):
        assert len(row) == w, f"{fid}: row {r} has {len(row)} cols (expected {w})"
    H = len(grid)
    start = None
    for j in range(H):
        for i in range(w):
            if grid[j][i] in "SUD":
                start = (i, j)
                break
        if start:
            break
    seen = {start}
    q = [start]
    blocked = SOLID | set("PT")
    while q:
        i, j = q.pop()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < w and 0 <= b < H and (a, b) not in seen and grid[b][a] not in blocked:
                seen.add((a, b))
                q.append((a, b))
    bad = [(i, j, grid[j][i]) for j in range(H) for i in range(w) if grid[j][i] in "SUDCBO" and (i, j) not in seen]
    assert not bad, f"{fid}: unreachable {bad}"


# ------------------------------------------------------------------ シーン
world = bpy.data.scenes["World"]
if "Interiors" in bpy.data.collections:
    old = bpy.data.collections["Interiors"]
    for ob in list(old.all_objects):
        bpy.data.objects.remove(ob)
    bpy.data.collections.remove(old)
C_INT = bpy.data.collections.new("Interiors")
world.collection.children.link(C_INT)

M_CROCK = mat("CaveRock", (0.42, 0.38, 0.34), 0.92)
M_CROCK2 = mat("CaveRockDark", (0.27, 0.24, 0.22), 0.95)
M_CFLOOR = mat("CaveFloor", (0.36, 0.32, 0.28), 0.9)
M_CRYSTAL = mat("CaveCrystal", (0.3, 0.85, 1.0), 0.15, emit=(0.25, 0.8, 1.0), emit_strength=5.0)
M_SHROOM = mat("GlowShroom", (0.4, 1.0, 0.75), 0.4, emit=(0.3, 1.0, 0.7), emit_strength=3.0)
M_CWATER = mat("CaveWater", (0.04, 0.12, 0.2), 0.04)
M_TSTONE = mat("TowerStone", (0.30, 0.27, 0.34), 0.9)
M_TFLOOR = mat("StoneFloor", (0.66, 0.63, 0.58), 0.9)
M_TTRIM = mat("StoneDark", (0.52, 0.50, 0.48), 0.9)
M_TCARPET = mat("TowerCarpet", (0.42, 0.06, 0.2), 0.95)
M_GOLD = mat("Gold", (1.0, 0.78, 0.25), 0.3, 1.0)
M_IRON = mat("Iron", (0.12, 0.12, 0.13), 0.5, 0.8)
M_WOOD = mat("Wood", (0.42, 0.27, 0.14), 0.8)
M_WOOD_D = mat("WoodDark", (0.25, 0.15, 0.08), 0.8)
M_MAGIC = mat("MagicGlow", (0.75, 0.35, 1.0), 0.2, emit=(0.75, 0.30, 1.0), emit_strength=4.0)
M_SLIT = mat("MoonSlit", (0.5, 0.65, 1.0), 0.5, emit=(0.45, 0.6, 1.0), emit_strength=2.5)
M_BANNER = mat("TowerBanner", (0.35, 0.05, 0.4), 0.8, double=True)
M_DARK = mat("Abyss", (0.0, 0.0, 0.0), 1.0)
M_DAYLIGHT = mat("Daylight", (1.0, 0.95, 0.8), 0.5, emit=(1.0, 0.92, 0.75), emit_strength=2.5)
M_ORB = mat("LightOrb", (1.0, 0.9, 0.5), 0.1, emit=(1.0, 0.85, 0.4), emit_strength=8.0)


def build_floor(index, fid, name, kind, grid):
    validate(fid, grid)
    rng = random.Random(index * 101 + 7)
    W, Hh = len(grid[0]), len(grid)
    ox, oz = 2000.0 + index * 250.0, 0.0
    root = empty("INT_" + fid, C_INT, B(ox, oz, 0))

    def cell(i, j):
        if 0 <= i < W and 0 <= j < Hh:
            return grid[j][i]
        return '#'

    def center(i, j):
        return (i + 0.5) * CELL, (j + 0.5) * CELL   # フロア原点からのローカル座標

    def L(x, z, y=0.0):
        return B(x, z, y)

    wall_h = 7.0 if kind == 'cave' else 6.0
    floor_mb, wall_mb, deco_mb, water_mb = MB(), MB(), MB(), MB()
    info = {"id": fid, "name": name, "kind": kind, "origin": [ox, oz], "cell": CELL, "grid": grid,
            "torches": [], "chests": [], "spots": {}, "lights": []}

    for j in range(Hh):
        for i in range(W):
            c = cell(i, j)
            cx, cz = center(i, j)
            if c in "SUDCBO":
                info["spots"].setdefault(c, []).append([ox + cx, oz + cz])
            # ---------------- 床
            if c != '#':
                if c == 'W':
                    water_mb.add('cube', M_CWATER, loc=L(cx, cz, -0.35), scale=(CELL, CELL, 0.1))
                    floor_mb.add('cube', M_CROCK2, loc=L(cx, cz, -1.2), scale=(CELL, CELL, 0.4))
                else:
                    n = 4
                    verts, faces = [], []
                    for b in range(n + 1):
                        for a in range(n + 1):
                            x = cx - CELL / 2 + a * CELL / n
                            z = cz - CELL / 2 + b * CELL / n
                            y = 0.0
                            if kind == 'cave':
                                y = (math.sin(x * 1.7 + ox) * math.cos(z * 1.3) * 0.05)
                            verts.append(L(x, z, y))
                    for b in range(n):
                        for a in range(n):
                            k = b * (n + 1) + a
                            faces.append((k, k + n + 1, k + n + 2, k + 1))
                    floor_mb.poly(verts, faces, M_CFLOOR if kind == 'cave' else M_TFLOOR, smooth=True)
                if c == 'R':
                    deco_mb.add('cube', M_TCARPET, loc=L(cx, cz, 0.03), scale=(CELL, CELL, 0.04))
            # ---------------- 壁
            if c == '#':
                near_floor = any(cell(i + di, j + dj) != '#' for di in (-1, 0, 1) for dj in (-1, 0, 1))
                if not near_floor:
                    continue
                if kind == 'cave':
                    # 土台の岩塊（セルを埋める）＋縦に伸びた岩柱で、ごつごつした洞窟の壁
                    wall_mb.add('ico', M_CROCK2, loc=L(cx, cz, 1.0), r=2.5, sub=2, rot=(0, 0, rng.uniform(0, 6.3)),
                                scale=(1.05, 1.05, 0.75), jitter=0.9, smooth=False, seed=i * 31 + j * 17)
                    for k in range(2):
                        rx, rz = cx + rng.uniform(-1.2, 1.2), cz + rng.uniform(-1.2, 1.2)
                        r = rng.uniform(1.1, 1.7)
                        wall_mb.add('ico', M_CROCK if k % 2 == 0 else M_CROCK2, loc=L(rx, rz, rng.uniform(2.0, 3.2)), r=r, sub=2,
                                    rot=(rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(0, 6.3)),
                                    scale=(rng.uniform(0.8, 1.2), rng.uniform(0.8, 1.2), rng.uniform(1.8, 2.6)), jitter=0.7, smooth=False,
                                    seed=i * 13 + j * 7 + k * 3)
                    if rng.random() < 0.12:
                        # 光る水晶
                        for k in range(rng.randint(2, 4)):
                            a = rng.uniform(0, math.tau)
                            deco_mb.add('ico', M_CRYSTAL, loc=L(cx + math.cos(a) * 1.6, cz + math.sin(a) * 1.6, rng.uniform(0.6, 2.5)), r=0.45, sub=0,
                                        rot=(rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), a), scale=(0.45, 0.45, 1.8), smooth=False)
                        info["lights"].append([ox + cx, 1.8, oz + cz, 0x40c8ff])
                else:
                    wall_mb.add('cube', M_TSTONE, loc=L(cx, cz, wall_h / 2), scale=(CELL, CELL, wall_h))
                    wall_mb.add('cube', M_TTRIM, loc=L(cx, cz, wall_h + 0.2), scale=(CELL + 0.2, CELL + 0.2, 0.4))
                    wall_mb.add('cube', M_TTRIM, loc=L(cx, cz, 0.25), scale=(CELL + 0.12, CELL + 0.12, 0.5))
                    # 内側を向いた面に窓（月明かり）や旗
                    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        if cell(i + di, j + dj) in ".RPCTSUDBO" and rng.random() < 0.18:
                            fx, fz = cx + di * (CELL / 2 + 0.02), cz + dj * (CELL / 2 + 0.02)
                            if rng.random() < 0.5:
                                sc = (0.06, 0.5, 2.0) if di else (0.5, 0.06, 2.0)
                                deco_mb.add('cube', M_SLIT, loc=L(fx, fz, 3.6), scale=sc)
                            else:
                                sc = (0.05, 1.4, 3.0) if di else (1.4, 0.05, 3.0)
                                deco_mb.add('cube', M_BANNER, loc=L(fx + di * 0.05, fz + dj * 0.05, 3.3), scale=sc)
                                deco_mb.add('ico', M_GOLD, loc=L(fx + di * 0.1, fz + dj * 0.1, 3.6), r=0.28, sub=1, scale=(1, 1, 1.2))
            # ---------------- 柱
            if c == 'P':
                deco_mb.add('cyl', M_TSTONE, loc=L(cx, cz, wall_h / 2), r1=0.75, r2=0.68, depth=wall_h, seg=16)
                deco_mb.add('cube', M_TTRIM, loc=L(cx, cz, 0.3), scale=(1.9, 1.9, 0.6))
                deco_mb.add('cube', M_TTRIM, loc=L(cx, cz, wall_h - 0.3), scale=(1.9, 1.9, 0.6))
            # ---------------- かがり火
            if c == 'T':
                if kind == 'cave':
                    deco_mb.add('ico', M_CROCK2, loc=L(cx, cz, 0.45), r=0.6, sub=1, scale=(1, 1, 0.8), jitter=0.1, smooth=False)
                    deco_mb.add('cyl', M_CROCK, loc=L(cx, cz, 1.0), r1=0.55, r2=0.7, depth=0.4, seg=10)
                else:
                    deco_mb.add('cyl', M_IRON, loc=L(cx, cz, 0.7), r1=0.12, r2=0.1, depth=1.4, seg=8)
                    deco_mb.add('cyl', M_IRON, loc=L(cx, cz, 0.08), r1=0.45, r2=0.35, depth=0.16, seg=10)
                    deco_mb.add('cyl', M_IRON, loc=L(cx, cz, 1.45), r1=0.35, r2=0.6, depth=0.35, seg=12)
                info["torches"].append([ox + cx, 1.75 if kind == 'tower' else 1.3, oz + cz])
            # ---------------- 階段・出口
            if c == 'U':
                for k in range(6):
                    hgt = 0.4 * (k + 1)
                    deco_mb.add('cube', M_CROCK2 if kind == 'cave' else M_TTRIM, loc=L(cx, cz + 1.65 - k * 0.62, hgt / 2),
                                scale=(CELL * 0.9, 0.62, hgt))
                deco_mb.add('cube', M_DARK, loc=L(cx, cz - CELL / 2 + 0.1, 3.2), scale=(CELL * 0.8, 0.1, 1.6))
            if c == 'D':
                floor_mb.add('cube', M_DARK, loc=L(cx, cz, -0.02), scale=(CELL * 0.8, CELL * 0.8, 0.06))
                for k in range(5):
                    deco_mb.add('cube', M_CROCK2 if kind == 'cave' else M_TTRIM, loc=L(cx, cz + 1.2 - k * 0.55, -0.15 - k * 0.3),
                                scale=(CELL * 0.75, 0.55, 0.3))
                for sx in (-1, 1):
                    deco_mb.add('cube', M_TTRIM if kind == 'tower' else M_CROCK2, loc=L(cx + sx * CELL * 0.45, cz, 0.3), scale=(0.3, CELL * 0.85, 0.6))
            if c == 'S':
                # 外の光（洞窟の入口／塔の扉）は外周の壁側に置く
                sd = 1 if j > Hh / 2 else -1
                deco_mb.add('cube', M_DAYLIGHT, loc=L(cx, cz + sd * (CELL / 2 + 0.6), 2.0), scale=(CELL * 0.95, 0.1, 4.0))
                info["lights"].append([ox + cx, 2.5, oz + cz + sd * 0.8, 0xfff0d0])
            if c == 'O':
                deco_mb.add('cyl', M_TTRIM, loc=L(cx, cz, 0.5), r1=0.8, r2=0.6, depth=1.0, seg=8)
                deco_mb.add('cyl', M_GOLD, loc=L(cx, cz, 1.05), r1=0.5, r2=0.55, depth=0.1, seg=16)
                info["lights"].append([ox + cx, 1.8, oz + cz, 0xffe090])
            if c == 'B' and kind == 'tower':
                deco_mb.add('cyl', M_MAGIC, loc=L(cx, cz, 0.02), r1=3.0, r2=3.0, depth=0.03, seg=32)
                deco_mb.add('cyl', M_TFLOOR, loc=L(cx, cz, 0.03), r1=2.75, r2=2.75, depth=0.035, seg=32)
            # ---------------- 洞窟の床の飾り（石筍・光るキノコ）
            if kind == 'cave' and c == '.':
                walls = sum(1 for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)) if cell(i + di, j + dj) == '#')
                if walls and rng.random() < 0.35:
                    a = rng.uniform(0, math.tau)
                    px, pz = cx + math.cos(a) * 1.5, cz + math.sin(a) * 1.5
                    deco_mb.add('cyl', M_CROCK, loc=L(px, pz, 0.6), r1=0.35, r2=0.03, depth=rng.uniform(0.8, 1.8), seg=7, jitter=0.05)
                if walls and rng.random() < 0.25:
                    a = rng.uniform(0, math.tau)
                    for k in range(3):
                        px, pz = cx + math.cos(a) * 1.4 + rng.uniform(-0.3, 0.3), cz + math.sin(a) * 1.4 + rng.uniform(-0.3, 0.3)
                        hh = rng.uniform(0.15, 0.35)
                        deco_mb.add('cyl', M_CFLOOR, loc=L(px, pz, hh / 2), r1=0.04, r2=0.04, depth=hh, seg=5)
                        deco_mb.add('sphere', M_SHROOM, loc=L(px, pz, hh), r=0.12, seg=8, rings=5, scale=(1, 1, 0.5))

    for nm, mb_ in (("Floor", floor_mb), ("Walls", wall_mb), ("Deco", deco_mb), ("Water", water_mb)):
        if mb_.bm.verts:
            ob = mb_.build(f"INT_{fid}_{nm}", C_INT)
            ob.location = (0, 0, 0)
            ob.parent = root
            # 子のメッシュはフロア原点（root）基準のローカル座標で作っている

    # 宝箱（ふたは別オブジェクト）
    k = 0
    for j in range(Hh):
        for i in range(W):
            if cell(i, j) != 'C':
                continue
            cx, cz = center(i, j)
            # 開いている側を向く
            rot = 0.0
            for (di, dj, r_) in ((0, 1, 0.0), (1, 0, math.pi / 2), (-1, 0, -math.pi / 2), (0, -1, math.pi)):
                if cell(i + di, j + dj) not in "#WP":
                    rot = r_
                    break
            cid = f"{fid}-{k}"
            mb = MB()
            mb.add('cube', M_WOOD, loc=(0, 0, 0.3), scale=(1.0, 0.66, 0.6))
            for sx in (-0.38, 0.38):
                mb.add('cube', M_GOLD, loc=(sx, 0, 0.3), scale=(0.08, 0.7, 0.62))
            mb.add('cube', M_GOLD, loc=(0, -0.34, 0.45), scale=(0.16, 0.04, 0.2))
            ch = mb.build(f"INT_{fid}_Chest{k}", C_INT, loc=L(cx, cz, 0), rot_z=rot, parent=root)
            mb = MB()
            mb.add('cube', M_WOOD_D, loc=(0, -0.33, 0.1), scale=(1.04, 0.68, 0.2))
            mb.add('cyl', M_WOOD, loc=(0, -0.33, 0.2), rot=(0, math.pi / 2, 0), r1=0.33, r2=0.33, depth=1.02, seg=16, scale=(0.55, 1, 1))
            for sx in (-0.38, 0.38):
                mb.add('cyl', M_GOLD, loc=(sx, -0.33, 0.2), rot=(0, math.pi / 2, 0), r1=0.345, r2=0.345, depth=0.08, seg=16, scale=(0.57, 1, 1))
            mb.build(f"INT_{fid}_Chest{k}_Lid", C_INT, loc=(0, 0.33, 0.6), parent=ch)
            info["chests"].append({"id": cid, "x": ox + cx, "z": oz + cz, "rot": rot})
            k += 1
    # ひかりのオーブ
    if 'O' in info["spots"]:
        x, z = info["spots"]['O'][0]
        mb = MB()
        mb.add('sphere', M_ORB, loc=(0, 0, 0), r=0.32, seg=24, rings=16)
        mb.add('ico', M_GOLD, loc=(0, 0, -0.3), r=0.22, sub=1, scale=(1.2, 1.2, 0.4))
        mb.build(f"INT_{fid}_Orb", C_INT, loc=L(x - ox, z - oz, 1.55), parent=root)
    return info


infos = [build_floor(k, *f) for k, f in enumerate(FLOORS)]
C_INT["data"] = json.dumps({"floors": infos}, ensure_ascii=False)
print("interiors done", [(i["id"], len(i["chests"]), len(i["torches"])) for i in infos])
