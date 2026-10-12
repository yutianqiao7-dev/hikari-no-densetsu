# -*- coding: utf-8 -*-
"""
Blender のシーンからゲーム用アセットを書き出す。
Blender で地形を彫刻したり、建物・木・COL_*(当たり判定)・MK_*(マーカー)を動かしたあとに実行すると
ゲームに反映される。

  public/assets/world.glb       地形・海・建物
  public/assets/props.glb       木・岩などのプロトタイプ
  public/assets/characters.glb  勇者・NPC・モンスター
  public/assets/world.json      高さマップ・配置・当たり判定・マーカー
"""
import bpy, json, os, math

ROOT = r"C:\Users\OWNER-1121R\Desktop\クロード\ドラクエ"
OUT = os.path.join(ROOT, "public", "assets")
os.makedirs(OUT, exist_ok=True)


def g(bx, by, bz):
    """Blender → ゲーム座標"""
    return [round(bx, 3), round(bz, 3), round(-by, 3)]


def export_glb(colls, path, vcol='ACTIVE', anim=False):
    """対象コレクションを一時的に現在のシーンへリンクし、選択して書き出す（シーン切替をしない＝バックグラウンドでも安定）"""
    scene = bpy.context.scene
    linked = []
    for c in colls:
        if c.name not in scene.collection.children:
            scene.collection.children.link(c)
            linked.append(c)
    bpy.context.view_layer.update()
    for ob in scene.objects:
        ob.select_set(False)
    for c in colls:
        for ob in coll_objects(c):
            ob.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, use_active_scene=True, export_apply=True,
        export_yup=True, export_vertex_color=vcol, export_cameras=False, export_lights=False,
        export_animations=anim, export_animation_mode='NLA_TRACKS', export_extras=False,
        export_skins=True, export_force_sampling=True, export_optimize_animation_size=True,
    )
    for c in linked:
        scene.collection.children.unlink(c)


def coll_objects(coll):
    obs = list(coll.objects)
    for c in coll.children:
        obs += coll_objects(c)
    return obs


world = bpy.data.scenes["World"]

if bpy.context.window:
    bpy.context.window.scene = world
export_glb([bpy.data.collections["Terrain"], bpy.data.collections["Buildings"]], os.path.join(OUT, "world.glb"))
export_glb([bpy.data.collections["Prototypes"]], os.path.join(OUT, "props.glb"), vcol='NONE')
export_glb([bpy.data.collections["Characters"]], os.path.join(OUT, "characters.glb"), vcol='NONE', anim=True)

# ---- world.json
terrain = bpy.data.objects["Terrain"]
me = terrain.data
nv = len(me.vertices)
n1 = int(round(math.sqrt(nv)))
xs = [v.co.x for v in me.vertices]
size = round(max(xs) - min(xs), 3)
heights = [round(v.co.z + terrain.location.z, 2) for v in me.vertices]

scatter = {}
for ob in bpy.data.collections["Scatter"].objects:
    if ob.instance_type != 'COLLECTION' or not ob.instance_collection:
        continue
    kind = ob.instance_collection.name
    p = g(*ob.location)
    scatter.setdefault(kind, []).append(p + [round(ob.rotation_euler.z, 3), round(ob.scale.x, 3), round(ob.scale.z, 3)])

colliders = []
for ob in bpy.data.collections["Colliders"].objects:
    x, y, z = g(*ob.location)
    colliders.append({
        "name": ob.name[4:], "x": x, "z": z,
        "hw": round(abs(ob.scale.x), 3), "hd": round(abs(ob.scale.y), 3),
        "rot": round(ob.rotation_euler.z, 4),
        "top": round(ob.location.z + abs(ob.scale.z), 2),
    })

markers = {}
for ob in bpy.data.collections["Markers"].objects:
    x, y, z = g(*ob.location)
    markers[ob.name[3:]] = {"x": x, "y": y, "z": z, "rot": round(ob.rotation_euler.z, 4)}

data = {
    "terrain": {"segments": n1 - 1, "size": size, "heights": heights},
    "scatter": scatter,
    "colliders": colliders,
    "markers": markers,
}
with open(os.path.join(OUT, "world.json"), "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

if bpy.context.window:
    bpy.context.window.scene = world
print("export done", {k: len(v) for k, v in scatter.items()}, len(colliders), "colliders", list(markers))
