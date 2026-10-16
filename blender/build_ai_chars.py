# -*- coding: utf-8 -*-
"""
ひかりの伝説 — 画像から AI で作った 3D モデル（import/*.glb）を仲間キャラにする

build_characters.py のあとに実行する。同じ名前の手作りキャラを消して、
  1. モデルを読み込み、足もとを原点に・ゲームの背の高さにそろえる
  2. モデルのポーズ（杖を持つ・腰に手）のまま、関節の位置に骨を入れる
  3. 骨の近さで体に重みをつける（自動）
ゲームでは、共通の骨格のアニメーションを「回転の差」として この骨に移す（src/actors/actor.js の retarget）。
骨の名前は共通の骨格と同じ。
"""
import os
import bpy, bmesh
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath or __file__)))
IMPORT = os.path.join(ROOT, "import")
COLL = bpy.data.collections["Characters"]

# 関節の位置（読み込んだモデルの座標。前は -y、上は z）
# center: 体の中心 (x, y)、sole: 足の裏の高さ、crown: 頭のてっぺん、height: ゲームでの背の高さ（m）
AI_CHARS = {
    'Milia': dict(
        file='milia.glb', center=(0.0, -0.07), sole=-0.505, height=1.62, x_offset=-2.0 - 9 * 1.5,
        crown=0.43, deform_cape=True,
        # 顔：元の絵の両目（画素）と、モデルの両目（x, z）。low = 目より下を縦にのばす割合、chin = あご（目の間隔の何倍下か）
        face=dict(ref='milia_ref.jpg', ref_eyes=((450.0, 162.5), (506.25, 161.25)),
                  eyes=((-0.0192, 0.3496), (0.024, 0.3496)), low=1.3, chin=1.5),
        bones={
            'hips': ((0, -0.06, -0.06), (0, -0.06, 0.03), None),
            'spine': ((0, -0.06, 0.03), (0, -0.07, 0.12), 'hips'),
            'chest': ((0, -0.07, 0.12), (0, -0.07, 0.235), 'spine'),
            'neck': ((0, -0.07, 0.235), (0, -0.075, 0.28), 'chest'),
            'head': ((0, -0.075, 0.28), (0, -0.075, 0.43), 'neck'),
            'shoulder.R': ((-0.02, -0.07, 0.21), (-0.10, -0.06, 0.21), 'chest'),
            'upper_arm.R': ((-0.10, -0.06, 0.21), (-0.18, -0.08, 0.05), 'shoulder.R'),
            'forearm.R': ((-0.18, -0.08, 0.05), (-0.235, -0.19, 0.11), 'upper_arm.R'),
            'hand.R': ((-0.235, -0.19, 0.11), (-0.25, -0.22, 0.13), 'forearm.R'),
            'shoulder.L': ((0.02, -0.07, 0.21), (0.10, -0.06, 0.21), 'chest'),
            'upper_arm.L': ((0.10, -0.06, 0.21), (0.13, -0.05, 0.08), 'shoulder.L'),
            'forearm.L': ((0.13, -0.05, 0.08), (0.075, -0.15, 0.055), 'upper_arm.L'),
            'hand.L': ((0.075, -0.15, 0.055), (0.05, -0.18, 0.05), 'forearm.L'),
            'thigh.L': ((0.05, -0.06, -0.06), (0.055, -0.06, -0.29), 'hips'),
            'shin.L': ((0.055, -0.06, -0.29), (0.06, -0.05, -0.46), 'thigh.L'),
            'foot.L': ((0.06, -0.05, -0.46), (0.06, -0.12, -0.50), 'shin.L'),
            'thigh.R': ((-0.05, -0.06, -0.06), (-0.06, -0.06, -0.29), 'hips'),
            'shin.R': ((-0.06, -0.06, -0.29), (-0.067, -0.05, -0.46), 'thigh.R'),
            'foot.R': ((-0.067, -0.05, -0.46), (-0.067, -0.12, -0.50), 'shin.R'),
            'cape.1': ((0, 0.06, 0.2), (0, 0.12, -0.1), 'chest'),
            'cape.2': ((0, 0.12, -0.1), (0, 0.16, -0.45), 'cape.1'),
        }),
    'Serena': dict(
        file='serena.glb', center=(0.016, -0.06), sole=-0.49, height=1.64, x_offset=-2.0 - 11 * 1.5,
        crown=0.5, deform_cape=False,
        face=dict(ref='serena_ref.jpg', ref_eyes=((391.25, 185.0), (471.25, 180.0)),
                  eyes=((-0.0156, 0.352), (0.0552, 0.3652)), low=1.0, chin=0.92),
        bones={
            'hips': ((0.016, -0.06, -0.06), (0.016, -0.06, 0.03), None),
            'spine': ((0.016, -0.06, 0.03), (0.016, -0.06, 0.13), 'hips'),
            'chest': ((0.016, -0.06, 0.13), (0.016, -0.06, 0.235), 'spine'),
            'neck': ((0.016, -0.06, 0.235), (0.016, -0.07, 0.29), 'chest'),
            'head': ((0.016, -0.07, 0.29), (0.016, -0.06, 0.5), 'neck'),
            'shoulder.R': ((0.0, -0.06, 0.235), (-0.08, -0.04, 0.235), 'chest'),
            'upper_arm.R': ((-0.08, -0.04, 0.235), (-0.11, -0.04, 0.115), 'shoulder.R'),
            'forearm.R': ((-0.11, -0.04, 0.115), (-0.185, -0.16, 0.10), 'upper_arm.R'),
            'hand.R': ((-0.185, -0.16, 0.10), (-0.21, -0.18, 0.10), 'forearm.R'),
            'shoulder.L': ((0.03, -0.06, 0.235), (0.11, -0.04, 0.235), 'chest'),
            'upper_arm.L': ((0.11, -0.04, 0.235), (0.205, -0.02, 0.13), 'shoulder.L'),
            'forearm.L': ((0.205, -0.02, 0.13), (0.13, -0.05, 0.09), 'upper_arm.L'),
            'hand.L': ((0.13, -0.05, 0.09), (0.11, -0.06, 0.08), 'forearm.L'),
            'thigh.L': ((0.07, -0.06, -0.06), (0.10, -0.06, -0.27), 'hips'),
            'shin.L': ((0.10, -0.06, -0.27), (0.125, -0.06, -0.45), 'thigh.L'),
            'foot.L': ((0.125, -0.06, -0.45), (0.125, -0.13, -0.49), 'shin.L'),
            'thigh.R': ((-0.04, -0.06, -0.06), (-0.05, -0.06, -0.27), 'hips'),
            'shin.R': ((-0.05, -0.06, -0.27), (-0.052, -0.06, -0.45), 'thigh.R'),
            'foot.R': ((-0.052, -0.06, -0.45), (-0.052, -0.13, -0.49), 'shin.R'),
            'cape.1': ((0.016, 0.03, 0.2), (0.016, 0.06, -0.05), 'chest'),
            'cape.2': ((0.016, 0.06, -0.05), (0.016, 0.1, -0.4), 'cape.1'),
        }),
}


def remove_old(name):
    for ob in list(bpy.data.objects):
        if ob.name == name or ob.name.startswith(name + "_"):
            bpy.data.objects.remove(ob)


def import_mesh(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    return meshes[0]


def paint_face(ob, spec):
    """元の絵の顔を、モデルの顔の正面から貼る（目・まゆ・鼻・口の線を絵のとおりに）"""
    import math
    import numpy as np
    f = spec.get('face')
    if not f:
        return
    me = ob.data
    tex_node = next(n for n in me.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE')
    img = tex_node.image
    W, H = img.size
    tex = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
    ref = bpy.data.images.load(os.path.join(IMPORT, f['ref']))
    RW, RH = ref.size
    rpx = np.array(ref.pixels[:], dtype=np.float32).reshape(RH, RW, 4)
    # 顔の向き（モデル）：両目を結ぶ線
    L3, R3 = Vector(f['eyes'][0]), Vector(f['eyes'][1])     # (x, z)
    mid3 = (L3 + R3) / 2
    e3 = R3 - L3
    d3 = e3.length
    ex3 = e3 / d3
    dn3 = Vector((ex3.y, -ex3.x))
    Lr, Rr = Vector(f['ref_eyes'][0]), Vector(f['ref_eyes'][1])  # 絵の画素（右・下）
    midr = (Lr + Rr) / 2
    er = Rr - Lr
    dr = er.length
    exr = er / dr
    dnr = Vector((-exr.y, exr.x))
    low, vchin = f.get('low', 1.0), f['chin']
    vtop = -0.72
    vc, hb = (vchin + vtop) / 2, (vchin - vtop) / 2

    def to_ref(X, Z):
        px, pz = X - mid3.x, Z - mid3.y
        u = (px * ex3.x + pz * ex3.y) / d3
        v = (px * dn3.x + pz * dn3.y) / d3
        vr = np.where(v < 0.15, v, 0.15 + (v - 0.15) / low)
        rx = midr.x + (u * exr.x + vr * dnr.x) * dr
        ry = midr.y + (u * exr.y + vr * dnr.y) * dr
        r = np.sqrt((u / 0.95) ** 2 + ((v - vc) / hb) ** 2)
        w = np.clip((1.0 - r) / 0.18, 0, 1)
        w = w * w * (3 - 2 * w)
        return rx, ry, w

    def sample(rx, ry):
        # 絵は下から上の行の並び（Blender）。双線形
        x = np.clip(rx - 0.5, 0, RW - 1.001)
        y = np.clip((RH - 1) - (ry - 0.5), 0, RH - 1.001)
        x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
        fx, fy = (x - x0)[..., None], (y - y0)[..., None]
        c = (rpx[y0, x0] * (1 - fx) * (1 - fy) + rpx[y0, x0 + 1] * fx * (1 - fy) +
             rpx[y0 + 1, x0] * (1 - fx) * fy + rpx[y0 + 1, x0 + 1] * fx * fy)
        return c[..., :3]
    uvl = me.uv_layers.active.data
    acc = np.zeros((H, W), np.float32)
    col = np.zeros((H, W, 3), np.float32)
    zlo, zhi = mid3.y - (vchin + 0.1) * d3 * 1.2, mid3.y + 0.9 * d3
    for p in me.polygons:
        vs = [me.vertices[i].co for i in p.vertices]
        if len(vs) != 3 or p.normal.y > -0.12:
            continue
        if not all(abs(v.x - mid3.x) < 1.2 * d3 and zlo < v.z < zhi for v in vs):
            continue
        nf = min(1.0, max(0.0, (-p.normal.y - 0.12) / 0.3))
        uvs = [uvl[li].uv for li in p.loop_indices]
        P = np.array([(u.x * W - 0.5, u.y * H - 0.5) for u in uvs])
        x0, y0 = np.floor(P.min(0)).astype(int)
        x1, y1 = np.ceil(P.max(0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        Y, X = np.mgrid[y0:y1 + 1, x0:x1 + 1].astype(np.float32)
        (ax, ay), (bx, by), (cx_, cy_) = P
        den = (by - cy_) * (ax - cx_) + (cx_ - bx) * (ay - cy_)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy_) * (X - cx_) + (cx_ - bx) * (Y - cy_)) / den
        l2 = ((cy_ - ay) * (X - cx_) + (ax - cx_) * (Y - cy_)) / den
        l3 = 1 - l1 - l2
        # 三角のふちの外 2 画素までぬる（UV のつなぎ目に古い絵の線が出ないように）
        e = [math.hypot(bx - cx_, by - cy_), math.hypot(cx_ - ax, cy_ - ay), math.hypot(ax - bx, ay - by)]
        tol = [2.0 * ei / abs(den) for ei in e]
        ins = (l1 >= -tol[0]) & (l2 >= -tol[1]) & (l3 >= -tol[2])
        if not ins.any():
            continue
        PX = l1 * vs[0].x + l2 * vs[1].x + l3 * vs[2].x
        PZ = l1 * vs[0].z + l2 * vs[1].z + l3 * vs[2].z
        rx, ry, w = to_ref(PX, PZ)
        w = w * nf * ins
        c = sample(rx, ry)
        sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        upd = w > acc[sl]
        acc[sl] = np.where(upd, w, acc[sl])
        col[sl] = np.where(upd[..., None], c, col[sl])
    m = acc > 0.01
    if not m.any():
        print("face paint: no texels")
        return
    # 肌の色をモデルにそろえる（線は残る）
    core = acc > 0.9
    gain = np.median(tex[core][:, :3], 0) / np.maximum(np.median(col[core], 0), 1e-3)
    gain = np.clip(gain, 0.75, 1.3)
    col = np.clip(col * (0.35 + 0.65 * gain), 0, 1)
    tex[..., :3] = tex[..., :3] * (1 - acc[..., None]) + col * acc[..., None]
    img.pixels.foreach_set(tex.ravel())
    img.pack()
    bpy.data.images.remove(ref)
    print("face paint:", int(m.sum()), "texels, gain", gain)


def build_ai(name, spec):
    path = os.path.join(IMPORT, spec['file'])
    if not os.path.exists(path):
        print("skip", name, "(no", path, ")")
        return None
    remove_old(name)
    ob = import_mesh(path)
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    COLL.objects.link(ob)
    ob.name = name + "_Body"
    ob.data.name = name + "_Body"
    ob.matrix_world = Matrix.Identity(4)
    paint_face(ob, spec)
    # 足もとを原点に、背の高さをそろえる
    cx, cy = spec['center']
    k = spec['height'] / (spec['crown'] - spec['sole'])
    M = Matrix.Scale(k, 4) @ Matrix.Translation(Vector((-cx, -cy, -spec['sole'])))

    def P(p):
        return M @ Vector(p)
    me = ob.data
    me.transform(M)
    # 面のつなぎ目をつなげて、なめらかに（AI のモデルは三角の面が角ばって見える）
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    for e in me.edges:
        e.use_edge_sharp = False
    # 材質・絵の名前（ゲームのトゥーン処理は名前で見分ける）
    for i, m in enumerate(me.materials):
        m.name = name + "_Look" + (str(i) if i else "")
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                n.image.name = name + "_LookTex"
                if not n.image.packed_file:
                    n.image.pack()
            if n.type == 'BSDF_PRINCIPLED':
                n.inputs['Roughness'].default_value = 0.7
                n.inputs['Metallic'].default_value = 0.0
        m.use_backface_culling = False
    # 骨
    arm = bpy.data.armatures.new(name + "_Rig")
    arm.display_type = 'STICK'
    arm_ob = bpy.data.objects.new(name, arm)
    COLL.objects.link(arm_ob)
    vl = bpy.context.view_layer
    if arm_ob.name not in vl.objects:
        bpy.context.scene.collection.objects.link(arm_ob)
    vl.objects.active = arm_ob
    with bpy.context.temp_override(active_object=arm_ob, object=arm_ob, selected_objects=[arm_ob], selected_editable_objects=[arm_ob]):
        bpy.ops.object.mode_set(mode='EDIT')
        for bn, (h, t, par) in spec['bones'].items():
            eb = arm.edit_bones.new(bn)
            eb.head = P(h)
            eb.tail = P(t)
            eb.roll = 0.0
        for bn, (h, t, par) in spec['bones'].items():
            eb = arm.edit_bones[bn]
            if par:
                eb.parent = arm.edit_bones[par]
            eb.use_deform = spec['deform_cape'] or not bn.startswith('cape')
        bpy.ops.object.mode_set(mode='OBJECT')
    return arm_ob, ob


def skin(arm_ob, ob):
    """骨の近さで自動の重み（うまくいかないときは、骨の線からの距離で）"""
    vl = bpy.context.view_layer
    for o in (arm_ob, ob):
        if o.name not in vl.objects:
            bpy.context.scene.collection.objects.link(o)
    for o in vl.objects:
        o.select_set(False)
    ob.select_set(True)
    arm_ob.select_set(True)
    vl.objects.active = arm_ob
    with bpy.context.temp_override(active_object=arm_ob, object=arm_ob, selected_objects=[ob, arm_ob],
                                   selected_editable_objects=[ob, arm_ob]):
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    weighted = sum(1 for v in ob.data.vertices if len(v.groups))
    print(ob.name, "auto weights:", weighted, "/", len(ob.data.vertices))
    if weighted < len(ob.data.vertices) * 0.95:
        print(ob.name, "-> distance weights")
        dist_weights(arm_ob, ob)


def dist_weights(arm_ob, ob):
    segs = []
    for b in arm_ob.data.bones:
        if b.use_deform:
            segs.append((b.name, Vector(b.head_local), Vector(b.tail_local)))
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {n: ob.vertex_groups.new(name=n) for n, _, _ in segs}
    for v in ob.data.vertices:
        p = v.co
        ds = []
        for n, a, b in segs:
            d = b - a
            t = max(0.0, min(1.0, (p - a).dot(d) / max(d.length_squared, 1e-9)))
            ds.append(((a + d * t - p).length, n))
        ds.sort()
        best = ds[:3]
        ws = [1.0 / max(d, 0.004) ** 4 for d, _ in best]
        s = sum(ws)
        for (d, n), w in zip(best, ws):
            if w / s > 0.02:
                groups[n].add([v.index], w / s, 'REPLACE')


def main():
    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    scene_link = COLL.name not in bpy.context.scene.collection.children
    if scene_link:
        bpy.context.scene.collection.children.link(COLL)
    for name, spec in AI_CHARS.items():
        r = build_ai(name, spec)
        if not r:
            continue
        arm_ob, ob = r
        skin(arm_ob, ob)
        arm_ob.location = (spec['x_offset'], 0, 0)
        print("AI character", name, "faces", len(ob.data.polygons))
    if scene_link:
        bpy.context.scene.collection.children.unlink(COLL)


main()
