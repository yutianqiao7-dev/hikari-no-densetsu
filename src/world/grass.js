import * as THREE from 'three';
import { NO_AO } from '../core/renderer.js';
import { NOISE } from './glsl.js';

/**
 * プレイヤー周辺に敷き詰める草と花（GPU インスタンシング）。
 * インスタンスは一辺 T の正方形タイル内に置かれ、シェーダーでプレイヤー中心に折り返して無限に敷き詰める。
 * 地形の色テクスチャが「草っぽい緑」の場所だけに生える。
 */
function makeField({ count, radius, blade, hf, heightTex, colorTex, shared, flower = false, hMin = 0.22, hVar = 0.32, wMin = 0.045, wVar = 0.035, inner = 0 }) {
  const T = radius * 2;
  const geo = new THREE.InstancedBufferGeometry();
  geo.index = blade.index;
  geo.attributes.position = blade.attributes.position;
  geo.attributes.normal = blade.attributes.normal;
  if (blade.attributes.color) geo.attributes.color = blade.attributes.color;
  const off = new Float32Array(count * 2);
  const rnd = new Float32Array(count * 4);
  for (let i = 0; i < count; i++) {
    off[i * 2] = Math.random() * T;
    off[i * 2 + 1] = Math.random() * T;
    rnd[i * 4] = Math.random(); rnd[i * 4 + 1] = Math.random(); rnd[i * 4 + 2] = Math.random(); rnd[i * 4 + 3] = Math.random();
  }
  geo.setAttribute('aOffset', new THREE.InstancedBufferAttribute(off, 2));
  geo.setAttribute('aRand', new THREE.InstancedBufferAttribute(rnd, 4));
  geo.instanceCount = count;

  const uni = {
    uCenter: { value: new THREE.Vector2() },
    uTile: { value: T },
    uRadius: { value: radius },
    uHeight: { value: heightTex },
    uColor: { value: colorTex },
    uHF: { value: hf.uvParams },
    uPlayer: { value: new THREE.Vector3() },
  };
  const mat = new THREE.MeshStandardMaterial({ roughness: 0.7, metalness: 0, side: THREE.DoubleSide, vertexColors: !!flower });
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uni, shared);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', /* glsl */`
        #include <common>
        attribute vec2 aOffset;
        attribute vec4 aRand;
        uniform vec2 uCenter, uWind;
        uniform float uTile, uRadius, uTime;
        uniform sampler2D uHeight, uColor;
        uniform vec4 uHF;
        uniform vec3 uPlayer;
        varying vec3 vGCol;
        varying float vGY;
        varying float vGAO;
        ${NOISE}
        vec2 tuv(vec2 p) { return ((p + uHF.x) / uHF.y + 0.5) / uHF.z; }
      `)
      .replace('#include <beginnormal_vertex>', /* glsl */`
        vec2 rel = mod(aOffset - uCenter + uTile * 0.5, uTile) - uTile * 0.5;
        vec2 gxz = uCenter + rel;
        float gdist = length(rel);
        float gh = texture2D(uHeight, tuv(gxz)).r;
        vec4 tc = texture2D(uColor, tuv(gxz));
        float green = tc.g - max(tc.r * 1.04, tc.b * 1.3);
        float patchN = vnoise(gxz * 0.06);
        float mask = smoothstep(0.004, 0.035, green) * step(1.3, gh) * (1.0 - smoothstep(uRadius * 0.7, uRadius, gdist));
        ${inner > 0 ? `mask *= smoothstep(${(inner * 0.6).toFixed(2)}, ${inner.toFixed(2)}, gdist);` : ''}
        ${flower ? 'mask *= smoothstep(0.58, 0.75, vnoise(gxz * 0.09 + 13.0)) * step(0.3, aRand.z);' : ''}
        float hgt = (${flower ? '0.22 + aRand.x * 0.22' : `${hMin.toFixed(3)} + aRand.x * ${hVar.toFixed(3)}`}) * mask * (0.7 + 0.6 * patchN);
        float ang = aRand.y * 6.2831853;
        vec3 objectNormal = normalize(vec3(sin(ang) * 0.6, 1.0, cos(ang) * 0.6));
      `)
      .replace('#include <begin_vertex>', /* glsl */`
        float yy = clamp(position.y, 0.0, 1.0);
        vec3 lp = vec3(position.x * ${flower ? '1.0' : `(${wMin.toFixed(3)} + aRand.z * ${wVar.toFixed(3)})`} , position.y * hgt, position.z * ${flower ? '1.0' : '0.0'});
        ${flower ? 'lp.xz *= mask * (0.8 + aRand.w * 0.5); lp.y = position.y * hgt;' : ''}
        float ca = cos(ang), sa = sin(ang);
        lp.xz = mat2(ca, -sa, sa, ca) * lp.xz;
        float gust = vnoise(gxz * 0.05 + uWind * uTime * 0.35);
        float w = sin(uTime * 2.1 + dot(gxz, uWind) * 0.35 + aRand.w * 6.28) * 0.35 + gust * 1.1;
        vec2 bend = uWind * w * 0.38 * yy * yy * hgt;
        vec2 away = gxz - uPlayer.xz;
        float pd = length(away);
        bend += (away / max(pd, 0.001)) * (1.0 - smoothstep(0.25, 1.3, pd)) * 0.55 * yy * hgt;
        lp.xz += bend;
        lp.y -= length(bend) * 0.45 * yy;
        vec3 transformed = vec3(gxz.x, gh - 0.02, gxz.y) + lp;
        vGCol = tc.rgb;
        vGY = yy;
        vGAO = 0.55 + 0.45 * patchN;
      `);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vGCol;\nvarying float vGY;\nvarying float vGAO;')
      .replace('#include <color_fragment>', flower ? /* glsl */`
        #include <color_fragment>
        diffuseColor.rgb *= mix(0.7, 1.0, vGY);
      ` : /* glsl */`
        vec3 base = vGCol * 0.72;
        vec3 tip = vGCol * 1.18 + vec3(0.035, 0.04, 0.0);
        diffuseColor.rgb = mix(base * vGAO, tip, smoothstep(0.0, 1.0, vGY));
      `);
  };
  const key = `grass-${flower}-${hMin}-${hVar}-${wMin}-${wVar}-${inner}`;
  mat.customProgramCacheKey = () => key;
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  mesh.receiveShadow = true;
  mesh.userData.uni = uni;
  NO_AO.add(mesh);
  return mesh;
}

function bladeGeometry() {
  const p = [], idx = [];
  const segs = 4;
  for (let s = 0; s <= segs; s++) {
    const y = s / segs;
    if (s < segs) { p.push(-0.5 * (1 - y * 0.9), y, 0, 0.5 * (1 - y * 0.9), y, 0); }
    else p.push(0, 1, 0);
  }
  for (let s = 0; s < segs - 1; s++) {
    const a = s * 2;
    idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
  }
  const a = (segs - 1) * 2;
  idx.push(a, a + 1, a + 2);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(p, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(new Array(p.length).fill(0).map((_, i) => (i % 3 === 2 ? 1 : 0)), 3));
  g.setIndex(idx);
  return g;
}

function flowerGeometry() {
  // 茎 + 5 枚の花びら + 中心
  const pos = [], col = [], idx = [];
  const stem = [0.32, 0.55, 0.2];
  const add = (x, y, z, c) => { pos.push(x, y, z); col.push(...c); return pos.length / 3 - 1; };
  const s0 = add(-0.012, 0, 0, stem), s1 = add(0.012, 0, 0, stem), s2 = add(0, 1, 0, stem);
  idx.push(s0, s1, s2);
  const petal = [1, 1, 1];
  const c = add(0, 1.02, 0, [1.0, 0.82, 0.2]);
  for (let k = 0; k < 5; k++) {
    const a = (k / 5) * Math.PI * 2, b = a + 0.5, d = a - 0.5;
    const p1 = add(Math.cos(d) * 0.05, 1.0, Math.sin(d) * 0.05, petal);
    const p2 = add(Math.cos(a) * 0.1, 1.04, Math.sin(a) * 0.1, petal);
    const p3 = add(Math.cos(b) * 0.05, 1.0, Math.sin(b) * 0.05, petal);
    idx.push(c, p1, p2, c, p2, p3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

export function createGrass(q, hf, heightTex, colorTex, shared) {
  const blade = bladeGeometry();
  const nearR = Math.max(14, q.grassRadius * 0.36);
  // 足元：短く密な草 / 遠景：幅広でまばらな草（境目はフェードで重ねる）
  const near = makeField({ count: Math.floor(q.grass * 0.62), radius: nearR, blade, hf, heightTex, colorTex, shared, hMin: 0.16, hVar: 0.26, wMin: 0.035, wVar: 0.03 });
  const far = makeField({ count: Math.floor(q.grass * 0.38), radius: q.grassRadius, blade, hf, heightTex, colorTex, shared, hMin: 0.28, hVar: 0.3, wMin: 0.1, wVar: 0.08, inner: nearR * 0.8 });
  const fgeo = flowerGeometry();
  const fields = [near, far];
  // 花の色ごとに 4 種
  const palette = [[1.0, 1.0, 1.0], [1.0, 0.85, 0.2], [1.0, 0.5, 0.65], [0.55, 0.65, 1.0]];
  for (const pc of palette) {
    const g = fgeo.clone();
    const cols = g.attributes.color;
    // 頂点 0-2 は茎、3 は花の中心、4 以降が花びら
    for (let k = 4; k < cols.count; k++) cols.setXYZ(k, ...pc);
    fields.push(makeField({ count: Math.floor(q.flowers / 4), radius: q.grassRadius * 0.9, blade: g, hf, heightTex, colorTex, shared, flower: true }));
  }
  const group = new THREE.Group();
  fields.forEach((f) => group.add(f));
  group.update = (center, player) => {
    for (const f of fields) {
      f.userData.uni.uCenter.value.set(center.x, center.z);
      f.userData.uni.uPlayer.value.copy(player);
    }
  };
  return group;
}
