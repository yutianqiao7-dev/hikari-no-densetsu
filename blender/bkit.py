# -*- coding: utf-8 -*-
"""ひかりの伝説 — Blender スクリプト共通ユーティリティ"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler, noise

# ---------------------------------------------------------------- 共通
def srgb(c):
    return tuple((v ** 2.2) for v in c)

def principled(m):
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return bsdf


_mats = {}
def mat(name, color, rough=0.8, metal=0.0, emit=None, emit_strength=1.0, double=False):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_backface_culling = not double
    bsdf = principled(m)
    bsdf.inputs["Base Color"].default_value = (*srgb(color), 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*srgb(emit), 1)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    m.diffuse_color = (*srgb(color), 1)
    _mats[name] = m
    return m


def vcol_mat(name):
    m = bpy.data.materials.new(name)
    m.use_backface_culling = True
    bsdf = principled(m)
    nt = m.node_tree
    bsdf.inputs["Roughness"].default_value = 0.95
    ca = nt.nodes.new("ShaderNodeVertexColor")
    ca.layer_name = "Color"
    nt.links.new(ca.outputs["Color"], bsdf.inputs["Base Color"])
    return m


class MB:
    """複数のプリミティブを1つのメッシュに組み立てる"""
    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def _mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def _merge(self, tmp, m, smooth, M, jitter=0.0, seed=0):
        bmesh.ops.transform(tmp, matrix=M, verts=tmp.verts)
        tmp.normal_update()
        mi = self._mi(m)
        vm = {}
        for v in tmp.verts:
            co = v.co.copy()
            if jitter:
                n = noise.noise(co * 2.3 + Vector((seed, seed * 0.7, 0)))
                co += v.normal * n * jitter
            vm[v] = self.bm.verts.new(co)
        for f in tmp.faces:
            try:
                nf = self.bm.faces.new([vm[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = mi
            nf.smooth = smooth
        tmp.free()

    def add(self, kind, m, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), smooth=None, jitter=0.0, **kw):
        tmp = bmesh.new()
        if kind == 'cube' and kw.get('bevel'):
            # 角を面取りした箱：先に寸法を確定してから一定幅で面取りする
            bmesh.ops.create_cube(tmp, size=1.0)
            bmesh.ops.scale(tmp, vec=Vector(scale), verts=tmp.verts)
            bw = min(kw['bevel'], min(scale) * 0.45)
            bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=bw, segments=kw.get('bseg', 1), profile=0.5, affect='EDGES')
            tmp.normal_update()
            M = Matrix.LocRotScale(Vector(loc), Euler(rot), Vector((1, 1, 1)))
            self._merge(tmp, m, False if smooth is None else smooth, M, jitter, kw.get('seed', 0))
            return
        if kind == 'cube':
            bmesh.ops.create_cube(tmp, size=1.0)
            sm = False
        elif kind == 'cyl':
            bmesh.ops.create_cone(tmp, cap_ends=True, cap_tris=False, segments=kw.get('seg', 16),
                                  radius1=kw.get('r1', 0.5), radius2=kw.get('r2', 0.5), depth=kw.get('depth', 1.0))
            sm = True
        elif kind == 'sphere':
            bmesh.ops.create_uvsphere(tmp, u_segments=kw.get('seg', 20), v_segments=kw.get('rings', 12), radius=kw.get('r', 0.5))
            sm = True
        elif kind == 'ico':
            bmesh.ops.create_icosphere(tmp, subdivisions=kw.get('sub', 2), radius=kw.get('r', 0.5))
            sm = True
        else:
            raise ValueError(kind)
        tmp.normal_update()
        M = Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(scale))
        self._merge(tmp, m, sm if smooth is None else smooth, M, jitter, kw.get('seed', 0))

    def poly_uv(self, verts, faces, uvs, m, smooth=True):
        """UV（頂点ごと）付きで面を足す（模様のテクスチャを貼る布用）"""
        uvl = self.bm.loops.layers.uv.get("UVMap") or self.bm.loops.layers.uv.new("UVMap")
        mi = self._mi(m)
        vs = [self.bm.verts.new(Vector(v)) for v in verts]
        for f in faces:
            try:
                nf = self.bm.faces.new([vs[i] for i in f])
            except ValueError:
                continue
            nf.material_index = mi
            nf.smooth = smooth
            for lp, i in zip(nf.loops, f):
                lp[uvl].uv = uvs[i]

    def poly(self, verts, faces, m, smooth=False, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
        tmp = bmesh.new()
        vs = [tmp.verts.new(v) for v in verts]
        for f in faces:
            tmp.faces.new([vs[i] for i in f])
        tmp.normal_update()
        M = Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(scale))
        self._merge(tmp, m, smooth, M)

    def tube(self, pts, radii, m, seg=16, smooth=True, flat=1.0):
        """点列に沿った滑らかなチューブ（首・尻尾など）"""
        verts, faces = [], []
        pts = [Vector(p) for p in pts]
        n = len(pts)
        side = None
        for i in range(n):
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            if side is None:
                side = t.cross(Vector((0, 0, 1)))
                if side.length < 1e-3:
                    side = t.cross(Vector((0, 1, 0)))
            else:  # 平行移動フレーム（ねじれ防止）
                side = side - t * side.dot(t)
            side.normalize()
            nup = side.cross(t).normalized()
            for k in range(seg):
                a = k / seg * math.tau
                off = side * math.cos(a) * radii[i] + nup * math.sin(a) * radii[i] * flat
                verts.append(tuple(pts[i] + off))
        for i in range(n - 1):
            for k in range(seg):
                a = i * seg + k
                b = i * seg + (k + 1) % seg
                faces.append((a, a + seg, b + seg, b))
        verts.append(tuple(pts[0]))
        verts.append(tuple(pts[-1]))
        c0, c1 = len(verts) - 2, len(verts) - 1
        for k in range(seg):
            faces.append((c0, k, (k + 1) % seg))
            faces.append((c1, (n - 1) * seg + (k + 1) % seg, (n - 1) * seg + k))
        self.poly(verts, faces, m, smooth=smooth)

    def deform(self, fn):
        for v in self.bm.verts:
            v.co = Vector(fn(v.co.copy()))

    def build(self, name, coll, loc=(0, 0, 0), rot_z=0.0, parent=None):
        bm = self.bm
        bm.normal_update()
        for e in bm.edges:
            if len(e.link_faces) == 2:
                a, b = e.link_faces
                if a.normal.angle(b.normal, 0) > math.radians(62) or not (a.smooth and b.smooth):
                    e.smooth = False
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (0, 0, rot_z)
        if parent:
            ob.parent = parent
        return ob


def empty(name, coll, loc=(0, 0, 0), parent=None, rot_z=0.0, size=0.5):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    coll.objects.link(e)
    e.location = loc
    e.rotation_euler = (0, 0, rot_z)
    if parent:
        e.parent = parent
    return e


def B(x, z, y=0.0):
    """ゲーム座標 (x, y, z) → Blender 座標"""
    return (x, -z, y)


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t

