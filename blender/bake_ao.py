# -*- coding: utf-8 -*-
"""
キャラ・モンスターのすき間の陰（AO）を頂点の色「AO」に焼き込む（Cycles）。
服の重なり・わきの下・襟の内側などが暗くなり、のっぺりしなくなる。

  blender -b world.blend --python build_characters.py --python bake_ao.py --python-expr "import bpy; bpy.ops.wm.save_mainfile()"
"""
import bpy, re, time

sc = bpy.data.scenes["Characters"]
coll = bpy.data.collections["Characters"]
SKIP = re.compile(r"_(Eye[LR]|Blush[LR])$")

sc.render.engine = 'CYCLES'
sc.cycles.samples = 48
try:
    sc.cycles.device = 'CPU'
except Exception:
    pass
if sc.world is None:
    sc.world = bpy.data.worlds.new("CharWorld")
sc.world.light_settings.distance = 0.12      # 近くのすき間だけ（となりのキャラの影は入れない）

# 骨格は初期姿勢のまま焼く
arms = [o for o in sc.objects if o.type == 'ARMATURE']
for a in arms:
    a.data.pose_position = 'REST'

meshes = [o for o in coll.all_objects if o.type == 'MESH' and not SKIP.search(o.name) and len(o.data.polygons) > 0]
vl = sc.view_layers[0]
t0 = time.time()
import sys
only = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else None
if only:
    meshes = [m for m in meshes if m.name.startswith(only)]
for o in sc.objects:
    o.select_set(False, view_layer=vl)
if True:
    for i, ob in enumerate(meshes):
        me = ob.data
        attr = me.color_attributes.get("AO")
        if attr is not None and attr.domain != 'POINT':
            me.color_attributes.remove(attr)
            attr = None
        if attr is None:
            # 頂点ごと（面の角ごとにすると頂点が分かれてデータが何倍にもなる）
            attr = me.color_attributes.new("AO", 'BYTE_COLOR', 'POINT')
        me.color_attributes.active_color = attr
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
        ob.select_set(True, view_layer=vl)
        vl.objects.active = ob
        try:
            with bpy.context.temp_override(scene=sc, view_layer=vl, active_object=ob, object=ob,
                                           selected_objects=[ob], selected_editable_objects=[ob]):
                bpy.ops.object.bake(type='AO', target='VERTEX_COLORS', use_clear=True)
        except Exception as e:
            print("bake failed", ob.name, e)
        ob.select_set(False, view_layer=vl)
        if i % 20 == 0:
            print(f"AO {i + 1}/{len(meshes)}  {time.time() - t0:.0f}s")
for a in arms:
    a.data.pose_position = 'POSE'
print("ao done", len(meshes), f"{time.time() - t0:.0f}s")
