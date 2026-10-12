import * as THREE from 'three';
import { leafTexture } from './leaves.js';

/** プロトタイプ（Group / Mesh）からメッシュ部品のリストを取り出す */
function partsOf(obj) {
  const out = [];
  obj.updateMatrixWorld(true);
  obj.traverse((o) => {
    if (o.isMesh) {
      const g = o.geometry.clone();
      g.applyMatrix4(o.matrixWorld);
      out.push({ geometry: g, material: o.material });
    }
  });
  return out;
}

function windify(material, shared, strength, aoRange) {
  const m = material.clone();
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, shared);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nuniform float uTime;\nuniform vec2 uWind;\nvarying float vLeafAO;')
      .replace('#include <begin_vertex>', /* glsl */`
        #include <begin_vertex>
        #ifdef USE_INSTANCING
          vec3 ip = instanceMatrix[3].xyz;
        #else
          vec3 ip = vec3(0.0);
        #endif
        float hk = max(position.y - 1.5, 0.0);
        float ph = dot(ip.xz, vec2(0.13, 0.09));
        float sw = sin(uTime * 1.3 + ph) * 0.6 + sin(uTime * 2.7 + ph * 1.7 + position.x) * 0.25;
        transformed.xz += uWind * sw * hk * ${strength.toFixed(4)};
        transformed.y += sin(uTime * 3.1 + position.x * 2.0 + position.z * 2.0 + ph) * 0.03 * hk * ${strength.toFixed(4)} * 6.0;
        vLeafAO = smoothstep(${aoRange[0].toFixed(2)}, ${aoRange[1].toFixed(2)}, position.y + length(position.xz) * 0.35);
      `);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying float vLeafAO;')
      .replace('#include <color_fragment>', '#include <color_fragment>\ndiffuseColor.rgb *= 0.5 + 0.62 * vLeafAO;');
  };
  m.customProgramCacheKey = () => `wind-${strength}-${aoRange.join(',')}`;
  return m;
}

/**
 * 木・岩・茂み。種類×部品ごとに「近景用」「遠景用」の InstancedMesh を 1 つずつ持ち、
 * カメラの位置と向きに応じて表示するインスタンスを 1 本ずつ選び直す（描画コールを最小に）。
 */
export class Vegetation {
  constructor(propsScene, scatter, hf, shared, q) {
    this.group = new THREE.Group();
    this.q = q;
    this.colliders = [];
    this.kinds = [];
    this.near = q.label === '最高' ? 80 : q.label === '高' ? 58 : 40;
    this.far = q.far;
    const protos = {};
    for (const child of propsScene.children) protos[child.name] = child;
    const texBroad = leafTexture('broad'), texPine = leafTexture('pine');

    const prep = (kind, p) => {
      let mat = p.material;
      if (/^LeafCard/.test(mat.name)) {
        mat = mat.clone();
        mat.map = mat.name === 'LeafCardDark' ? texPine : texBroad;
        mat.alphaTest = 0.45;
        mat.alphaToCoverage = q.msaa > 0;
        mat.side = THREE.DoubleSide;
        mat.roughness = 0.75;
      }
      if (/Leaf/i.test(mat.name)) return windify(mat, shared, kind.includes('Pine') ? 0.012 : 0.02, kind === 'Bush' ? [0.0, 1.2] : [2.0, 6.5]);
      return mat.clone();
    };

    const up = new THREE.Vector3(0, 1, 0);
    for (const kind of Object.keys(scatter)) {
      const hi = protos[kind];
      if (!hi) continue;
      const lo = protos[kind + '_LOD'] || hi;
      const items = scatter[kind];
      const m4 = new THREE.Matrix4(), qt = new THREE.Quaternion(), sc = new THREE.Vector3(), ps = new THREE.Vector3();
      const mats = items.map(([x, y, z, rot, s, sy]) => m4.compose(ps.set(x, y, z), qt.setFromAxisAngle(up, rot), sc.set(s, sy, s)).clone());
      const tints = items.map(() => { const v = 0.85 + Math.random() * 0.3; return new THREE.Color(v * (0.95 + Math.random() * 0.1), v, v * (0.9 + Math.random() * 0.15)); });
      const pos = items.map(([x, , z]) => ({ x, z }));
      for (const [x, y, z, , s] of items) {
        if (kind.startsWith('Tree')) this.colliders.push({ x, z, r: 0.45 * s, tree: s, y });
        else if (kind === 'Rock') this.colliders.push({ x, z, r: 1.0 * s });
      }
      const mk = (proto, shadow) => partsOf(proto).map((p) => {
        const im = new THREE.InstancedMesh(p.geometry, prep(kind, p), items.length);
        im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        for (let i = 0; i < items.length; i++) im.setColorAt(i, tints[i]);
        im.count = 0;
        im.frustumCulled = false;
        im.castShadow = shadow;
        im.receiveShadow = true;
        this.group.add(im);
        return im;
      });
      this.kinds.push({ kind, mats, tints, pos, hi: mk(hi, true), lo: mk(lo, kind !== 'Bush') });
    }
    this.lastPos = new THREE.Vector3(1e9, 0, 0);
    this.lastDir = new THREE.Vector3();
    this.dir = new THREE.Vector3();
  }

  fill(list, idx, k) {
    for (const im of list) {
      for (let n = 0; n < idx.length; n++) { im.setMatrixAt(n, k.mats[idx[n]]); im.setColorAt(n, k.tints[idx[n]]); }
      im.count = idx.length;
      im.instanceMatrix.needsUpdate = true;
      if (im.instanceColor) im.instanceColor.needsUpdate = true;
    }
  }

  update(camPos, camera) {
    const dir = this.dir;
    if (camera) camera.getWorldDirection(dir); else dir.set(0, 0, -1);
    dir.y = 0;
    dir.normalize();
    if (camPos.distanceToSquared(this.lastPos) < 4 && dir.dot(this.lastDir) > 0.985) return;
    this.lastPos.copy(camPos);
    this.lastDir.copy(dir);
    const near2 = this.near * this.near, far2 = this.far * this.far;
    const halfFov = camera ? THREE.MathUtils.degToRad(camera.fov * 0.5) * Math.max(1, camera.aspect) : Math.PI;
    const cosLimit = Math.cos(Math.min(Math.PI, halfFov + 0.35));
    for (const k of this.kinds) {
      const hiIdx = [], loIdx = [];
      for (let i = 0; i < k.pos.length; i++) {
        const p = k.pos[i];
        const dx = p.x - camPos.x, dz = p.z - camPos.z;
        const d2 = dx * dx + dz * dz;
        if (d2 > far2) continue;
        const d = Math.sqrt(d2);
        // 視界の外（背後）は描かない。近くの木は影のために残す
        if (d > 30 && (dx * dir.x + dz * dir.z) / d < cosLimit) continue;
        if (d2 < near2) hiIdx.push(i); else loIdx.push(i);
      }
      this.fill(k.hi, hiIdx, k);
      this.fill(k.lo, loIdx, k);
    }
  }
}
