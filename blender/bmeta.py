# -*- coding: utf-8 -*-
"""メタボール造形の共通処理（キャラクター・モンスター用）"""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from bkit import MB

K = 0.57  # メタボール: 表面半径 ≒ radius * K（stiffness 2, threshold 0.6）
_target = {'coll': None}


def set_collection(coll):
    """メタボール評価・一時オブジェクトを置くコレクション（現在のシーンにリンクされていること）"""
    _target['coll'] = coll


class CMB(MB):
    """球は半径1を基準にし、scale を半径（半軸）として扱う"""
    def add(self, kind, m, *a, **kw):
        if kind == 'sphere' and 'r' not in kw:
            kw['r'] = 1.0
            kw.setdefault('seg', 24)
            kw.setdefault('rings', 14)
        return MB.add(self, kind, m, *a, **kw)


def E_ball(co, r):
    return ('b', Vector(co), r)


def E_cap(a, b, r):
    return ('c', Vector(a), Vector(b), r)


def E_ell(co, rx, ry, rz, rot=None):
    return ('e', Vector(co), (rx, ry, rz), rot or Quaternion())


def E_dir(co, d, r_along, r1, r2):
    q = Vector((0, 0, 1)).rotation_difference(Vector(d).normalized())
    return ('e', Vector(co), (r1, r2, r_along), q)


def E_chain(pts, radii):
    """点列に沿ったカプセルの連なり（首・尻尾・指など）"""
    out = []
    for i in range(len(pts) - 1):
        out.append(E_cap(pts[i], pts[i + 1], (radii[i] + radii[i + 1]) * 0.5))
    return out


def meta_mesh(name, elems, res=0.008):
    coll = _target['coll']
    mbd = bpy.data.metaballs.new("MBD_" + name)
    mbd.resolution = res
    mbd.render_resolution = res
    mbd.threshold = 0.6
    for el in elems:
        k = el[0]
        if k == 'b':
            e = mbd.elements.new(type='BALL')
            e.co = el[1]
            e.radius = el[2] / K
        elif k == 'c':
            a, b, r = el[1], el[2], el[3]
            e = mbd.elements.new(type='CAPSULE')
            e.co = (a + b) / 2
            e.radius = r / K
            e.size_x = max((b - a).length / 2, 1e-4)
            e.rotation = Vector((1, 0, 0)).rotation_difference((b - a).normalized())
        else:
            co, rr, q = el[1], el[2], el[3]
            m = max(rr)
            e = mbd.elements.new(type='ELLIPSOID')
            e.co = co
            e.radius = m / K
            e.size_x, e.size_y, e.size_z = rr[0] / m, rr[1] / m, rr[2] / m
            e.rotation = q
    ob = bpy.data.objects.new("MBO_" + name.replace(".", "_"), mbd)
    coll.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mbd)
    me.name = name
    return me


def decimate(me, target_faces):
    if len(me.polygons) <= target_faces:
        return me
    ob = bpy.data.objects.new("_dec", me)
    _target['coll'].objects.link(ob)
    mod = ob.modifiers.new("dec", 'DECIMATE')
    mod.ratio = target_faces / len(me.polygons)
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    name = me.name
    bpy.data.meshes.remove(me)
    me2.name = name
    return me2


def mesh_to_obj(me, name, smooth=True):
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    _target['coll'].objects.link(ob)
    return ob


class Surface:
    """メッシュ表面へのレイキャスト（顔のパーツ・ベルトなどを表面に沿わせる）"""
    def __init__(self, me):
        self.bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])

    def front(self, x, z, y0=-0.6):
        hit = self.bvh.ray_cast(Vector((x, y0, z)), Vector((0, 1, 0)))
        if hit[0] is None:
            return Vector((x, -0.1, z)), Vector((0, -1, 0))
        return hit[0], hit[1]

    def ray(self, origin, direction, maxd=10.0):
        hit = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized(), maxd)
        return hit[0], hit[1]

    def radial(self, center, ang, tilt=0.0, maxd=0.22):
        d = Vector((math.sin(ang), -math.cos(ang), tilt)).normalized()
        hit = self.bvh.ray_cast(Vector(center), d, maxd)
        if hit[0] is None:
            return Vector(center) + d * maxd, d
        return hit[0], hit[1]


def basis_euler(normal, up=Vector((0, 0, 1))):
    n = normal.normalized()
    right = up.cross(n).normalized() * -1
    if right.length < 1e-4:
        right = Vector((1, 0, 0))
    upv = n.cross(right).normalized() * -1
    m = Matrix((right, n, upv)).transposed()
    return m.to_euler()
