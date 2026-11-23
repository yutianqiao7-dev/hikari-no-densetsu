import * as THREE from 'three';
import { NO_AO } from '../core/renderer.js';
import { leafTexture } from './leaves.js';
import { enhanceSurface } from './surfaces.js';

/**
 * 葉の房（Gemini で描いた絵・2×2 のアトラス）を、いつもカメラのほうを向く板として木の形に並べる（ドラクエ10風のふんわりした木）。
 * 影を作るときは太陽のほうを向くので、影も房の形になる。
 */
let clumpTex = null;
function clumpTexture() {
  if (clumpTex) return clumpTex;
  clumpTex = new THREE.TextureLoader().load(`${import.meta.env.BASE_URL}assets/tex/leaves.png`);
  clumpTex.colorSpace = THREE.SRGBColorSpace;
  clumpTex.anisotropy = 4;
  return clumpTex;
}

/** 葉の房の板のジオメトリ：中心・すみ・大きさ・回転・絵の番号・向き（法線）を頂点ごとに持つ */
function clumpGeometry(center, rx, ry, n, seed) {
  let sd = seed;
  const rnd = () => { sd = (sd * 16807) % 2147483647; return sd / 2147483647; };
  const pos = [], nrm = [], corner = [], size = [], rot = [], tile = [], shade = [], idx = [];
  for (let i = 0; i < n; i++) {
    // 上ほど多く、外側に（丸い樹冠）
    const u = rnd() * 2 - 1, a = rnd() * Math.PI * 2;
    const y = Math.max(-0.55, u * 0.9 + 0.12);
    const rr = Math.sqrt(Math.max(0, 1 - y * y));
    const d = new THREE.Vector3(Math.cos(a) * rr, y, Math.sin(a) * rr);
    const k = i < 3 ? 0.3 : 0.55 + rnd() * 0.25;
    const p = new THREE.Vector3(center.x + d.x * rx * k, center.y + d.y * ry * k, center.z + d.z * rx * k);
    const s = (rx + ry) * 0.5 * (0.58 + rnd() * 0.24);
    const r = rnd() * Math.PI * 2, t = Math.floor(rnd() * 4);
    const base = pos.length / 3;
    for (const [cx, cy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      pos.push(p.x, p.y, p.z);
      nrm.push(d.x, d.y * 1.3 + 0.25, d.z);
      corner.push(cx, cy);
      size.push(s);
      rot.push(r);
      tile.push(t);
      // 内側・下側の房は暗く（木の中の陰）
      shade.push((0.55 + 0.3 * (y * 0.5 + 0.5)) * (0.7 + 0.3 * Math.min(1, k / 0.7)));
    }
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute('aCorner', new THREE.Float32BufferAttribute(corner, 2));
  g.setAttribute('aSize', new THREE.Float32BufferAttribute(size, 1));
  g.setAttribute('aRot', new THREE.Float32BufferAttribute(rot, 1));
  g.setAttribute('aTile', new THREE.Float32BufferAttribute(tile, 1));
  g.setAttribute('aShade', new THREE.Float32BufferAttribute(shade, 1));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(corner.length), 2));
  g.setIndex(idx);
  g.computeBoundingSphere();
  g.boundingSphere.radius += Math.max(rx, ry);
  return g;
}

const CLUMP_VERT = (shared) => /* glsl */`
  attribute vec2 aCorner;
  attribute float aSize, aRot, aTile, aShade;
  uniform float uTime;
  uniform vec2 uWind;
  varying vec2 vClumpUv;
  varying float vShade;
`;
const CLUMP_PROJECT = /* glsl */`
  vec4 cw = vec4(transformed, 1.0);
  #ifdef USE_INSTANCING
    cw = instanceMatrix * cw;
    float isc = length(instanceMatrix[0].xyz);
    vec3 ipos = instanceMatrix[3].xyz;
  #else
    float isc = 1.0;
    vec3 ipos = vec3(0.0);
  #endif
  // 風でゆれる（上のほうほど大きく）
  float ph = dot(ipos.xz, vec2(0.13, 0.09));
  cw.xz += uWind * (sin(uTime * 1.3 + ph) * 0.6 + sin(uTime * 2.6 + ph * 1.7 + aRot) * 0.3) * 0.05 * max(transformed.y - 1.0, 0.0);
  vec4 mvPosition = modelViewMatrix * cw;
  float cr = cos(aRot + sin(uTime * 1.7 + ph + aRot * 3.0) * 0.06), sr = sin(aRot + sin(uTime * 1.7 + ph + aRot * 3.0) * 0.06);
  vec2 off = mat2(cr, sr, -sr, cr) * aCorner;
  mvPosition.xy += off * aSize * isc;
  // 絵のはしは房どうしが重なるよう、すこし手前へ
  mvPosition.z += (1.0 - dot(aCorner, aCorner) * 0.5) * aSize * isc * 0.35;
  gl_Position = projectionMatrix * mvPosition;
  vClumpUv = (aCorner * 0.5 + 0.5) * 0.5 + vec2(mod(aTile, 2.0), floor(aTile / 2.0)) * 0.5;
  vShade = aShade;
`;

function clumpMaterial(shared, msaa, tint) {
  const m = new THREE.MeshStandardMaterial({ map: clumpTexture(), alphaTest: 0.5, roughness: 0.85, color: tint });
  m.name = 'LeafClump';
  m.alphaToCoverage = msaa > 0;
  const patch = (sh) => {
    Object.assign(sh.uniforms, shared);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\n' + CLUMP_VERT())
      .replace('#include <project_vertex>', CLUMP_PROJECT);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vClumpUv;\nvarying float vShade;')
      .replace('#include <map_fragment>', '#ifdef USE_MAP\n  vec4 sampledDiffuseColor = texture2D(map, vClumpUv);\n  diffuseColor *= sampledDiffuseColor;\n  diffuseColor.rgb *= vShade;\n#endif');
  };
  m.onBeforeCompile = patch;
  m.customProgramCacheKey = () => 'leafclump';
  // 影：太陽から見ても房の形
  const dm = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: m.map, alphaTest: 0.5 });
  dm.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, shared);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\n' + CLUMP_VERT())
      .replace('#include <project_vertex>', CLUMP_PROJECT);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vClumpUv;\nvarying float vShade;')
      .replace('#include <map_fragment>', '#ifdef USE_MAP\n  vec4 sampledDiffuseColor = texture2D(map, vClumpUv);\n  diffuseColor *= sampledDiffuseColor;\n#endif');
  };
  dm.customProgramCacheKey = () => 'leafclump-depth';
  return { m, dm };
}

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
      const c = mat.clone();
      // 岩にも手描きの岩肌（surfaces.js の rock）
      if (/Rock/.test(mat.name)) { const nm = c.name; c.name = 'CaveRock'; enhanceSurface(c, null, new THREE.Vector4()); c.name = nm; c.color.multiplyScalar(0.72); }
      return c;
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
        else if (/^Rock/.test(kind)) this.colliders.push({ x, z, r: 1.0 * s });
        else if (kind === 'Cactus') this.colliders.push({ x, z, r: 0.5 * s });
      }
      const broad = kind === 'Tree_Broad' || kind === 'Bush';
      const mk = (proto, shadow, lod) => partsOf(proto).map((p) => {
        let geo = p.geometry, mat = null, depth = null;
        // 広葉樹・茂み：葉の板（LeafCard）を、Gemini の葉の房に置きかえる
        if (broad && /^LeafCard/.test(p.material.name)) {
          geo.computeBoundingBox();
          const bb = geo.boundingBox, c = bb.getCenter(new THREE.Vector3()), sz = bb.getSize(new THREE.Vector3());
          geo = clumpGeometry(c, sz.x * 0.5, sz.y * 0.5, kind === 'Bush' ? (lod ? 6 : 10) : (lod ? 12 : 22), kind.length * 977 + (lod ? 3 : 7));
          // 絵の黄緑は明るすぎるので、深い緑に寄せる
          const cm = clumpMaterial(shared, q.msaa, new THREE.Color(0.62, 0.74, 0.5));
          mat = cm.m; depth = cm.dm;
        }
        const im = new THREE.InstancedMesh(geo, mat || prep(kind, p), items.length);
        if (depth) im.customDepthMaterial = depth;
        if (broad && /^LeafCore/.test(p.material.name)) im.material.color.multiplyScalar(0.55);
        im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        for (let i = 0; i < items.length; i++) im.setColorAt(i, tints[i]);
        im.count = 0;
        im.frustumCulled = false;
        im.castShadow = shadow;
        im.receiveShadow = true;
        this.group.add(im);
        const pm = im.material;
        if (pm.alphaTest > 0 || pm.transparent || /Leaf/.test(p.material.name || '')) NO_AO.add(im);
        return im;
      });
      this.kinds.push({ kind, mats, tints, pos, hi: mk(hi, true, false), lo: mk(lo, kind !== 'Bush', true) });
    }
    this.lastPos = new THREE.Vector3(1e9, 0, 0);
    this.lastDir = new THREE.Vector3();
    this.dir = new THREE.Vector3();
    this.exclude = null;
  }

  /** 戦闘中など、指定した円の中の木・岩を描かない（null で解除） */
  setExclude(center, radius) {
    this.exclude = center ? { x: center.x, z: center.z, r2: radius * radius } : null;
    this.lastPos.set(1e9, 0, 0);
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
        const ex = this.exclude;
        if (ex && (p.x - ex.x) ** 2 + (p.z - ex.z) ** 2 < ex.r2) continue;
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
