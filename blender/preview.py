# -*- coding: utf-8 -*-
"""プレビュー画像を書き出す:  blender -b world.blend --python preview.py -- <scene> <out.png> cx cy cz tx ty tz [lens]
座標は Blender 座標。"""
import bpy, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
scene = bpy.data.scenes[args[0]]
out = args[1]
loc = Vector(map(float, args[2:5]))
tgt = Vector(map(float, args[5:8]))
lens = float(args[8]) if len(args) > 8 else 35

cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
scene.collection.objects.link(cam)
cam.data.lens = lens
cam.data.clip_end = 5000
cam.location = loc
cam.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 960
scene.render.resolution_y = 540
if scene.world is None:
    scene.world = bpy.data.worlds.new("PreviewWorld")
scene.world.color = (0.45, 0.6, 0.85)
scene.render.filepath = out
with bpy.context.temp_override(scene=scene):
    bpy.ops.render.render(write_still=True, scene=scene.name)
