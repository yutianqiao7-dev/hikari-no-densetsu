import * as THREE from 'three';
import { NOISE } from './glsl.js';
import { isTextureLow } from './surfaces.js';

/**
 * 地面の手描きテクスチャ（Gemini で描いた絵 → scripts/process_gemini_tex.py）を 1 つの束（配列テクスチャ）にまとめる。
 * 並び：0 草地 / 1 森の草地 / 2 土 / 3 砂 / 4 雪 / 5 溶岩 / 6 岩
 */
const GROUND = ['g_grass', 'g_grass2', 'g_dirt', 'g_sand', 'g_snow', 'g_lava', 'rock'];
let groundSet = null;
function groundTextures() {
  if (groundSet) return groundSet;
  const S = isTextureLow() ? 512 : 1024;
  const mk = (srgb) => {
    const t = new THREE.DataArrayTexture(new Uint8Array(S * S * 4 * GROUND.length).fill(128), S, S, GROUND.length);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.minFilter = THREE.LinearMipmapLinearFilter;
    t.magFilter = THREE.LinearFilter;
    t.generateMipmaps = true;
    t.anisotropy = 8;
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.needsUpdate = true;
    return t;
  };
  groundSet = { a: mk(true), n: mk(false), ready: false };
  const cv = document.createElement('canvas');
  cv.width = cv.height = S;
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  const base = `${import.meta.env.BASE_URL}assets/tex/`;
  (async () => {
    for (const [key, suf] of [['a', 'a'], ['n', 'n']]) {
      const data = groundSet[key].image.data;
      for (let i = 0; i < GROUND.length; i++) {
        const blob = await (await fetch(`${base}${GROUND[i]}_${suf}.jpg`)).blob();
        const bmp = await createImageBitmap(blob);
        ctx.drawImage(bmp, 0, 0, S, S);
        data.set(ctx.getImageData(0, 0, S, S).data, i * S * S * 4);
      }
      groundSet[key].needsUpdate = true;
    }
    groundSet.ready = true;
  })().catch((e) => console.warn('ground textures', e));
  return groundSet;
}
const BIOME = { main: 0, desert: 1, ice: 2, volcano: 3, dark: 4 };

/** Blender で作った地形の高さマップ。三角形分割と一致した厳密な高さを返す */
export class Heightfield {
  constructor(t) {
    this.n = t.segments;
    this.w = this.n + 1;
    this.size = t.size;
    this.half = t.size / 2;
    this.step = t.size / this.n;
    this.h = Float32Array.from(t.heights);
  }
  at(i, j) {
    i = Math.max(0, Math.min(this.n, i));
    j = Math.max(0, Math.min(this.n, j));
    return this.h[j * this.w + i];
  }
  height(x, z) {
    const fx = (x + this.half) / this.step, fz = (z + this.half) / this.step;
    if (fx < 0 || fz < 0 || fx > this.n || fz > this.n) return -14;
    const i = Math.min(this.n - 1, Math.floor(fx)), j = Math.min(this.n - 1, Math.floor(fz));
    const tx = fx - i, tz = fz - j;
    const h00 = this.at(i, j), h10 = this.at(i + 1, j), h01 = this.at(i, j + 1), h11 = this.at(i + 1, j + 1);
    if (tx + tz <= 1) return h00 + (h10 - h00) * tx + (h01 - h00) * tz;
    return h11 + (h01 - h11) * (1 - tx) + (h10 - h11) * (1 - tz);
  }
  normal(x, z, out = new THREE.Vector3()) {
    const e = 0.75;
    return out.set(this.height(x - e, z) - this.height(x + e, z), 2 * e, this.height(x, z - e) - this.height(x, z + e)).normalize();
  }
  slope(x, z) {
    const e = 0.8;
    return Math.hypot(this.height(x + e, z) - this.height(x - e, z), this.height(x, z + e) - this.height(x, z - e)) / (2 * e);
  }
  /** シェーダー用 UV 変換係数 */
  get uvParams() { return new THREE.Vector4(this.half, this.step, this.w, 0); }
}

/**
 * Blender の地形メッシュから頂点カラーを取り出し、高さマップと同じ並びのテクスチャとジオメトリを作る
 */
export function buildTerrain(hf, gltfTerrainMesh, sharedIn = null, biome = 'main') {
  const W = hf.w;
  const colors = new Float32Array(W * W * 3).fill(0.3);
  const src = gltfTerrainMesh.geometry;
  const sp = src.attributes.position, sc = src.attributes.color;
  if (sc) {
    const m = gltfTerrainMesh.matrixWorld;
    const v = new THREE.Vector3();
    for (let k = 0; k < sp.count; k++) {
      v.fromBufferAttribute(sp, k).applyMatrix4(m);
      const i = Math.round((v.x + hf.half) / hf.step), j = Math.round((v.z + hf.half) / hf.step);
      if (i < 0 || j < 0 || i >= W || j >= W) continue;
      const o = (j * W + i) * 3;
      colors[o] = sc.getX(k); colors[o + 1] = sc.getY(k); colors[o + 2] = sc.getZ(k);
    }
  }

  // ジオメトリ（高さマップの三角形分割と一致させる）
  const pos = new Float32Array(W * W * 3);
  for (let j = 0; j < W; j++) for (let i = 0; i < W; i++) {
    const o = (j * W + i) * 3;
    pos[o] = -hf.half + i * hf.step;
    pos[o + 1] = hf.h[j * W + i];
    pos[o + 2] = -hf.half + j * hf.step;
  }
  const idx = new Uint32Array(hf.n * hf.n * 6);
  let q = 0;
  for (let j = 0; j < hf.n; j++) for (let i = 0; i < hf.n; i++) {
    const a = j * W + i, b = a + 1, c = a + W, d = c + 1;
    idx[q++] = a; idx[q++] = c; idx[q++] = b;
    idx[q++] = b; idx[q++] = c; idx[q++] = d;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geo.setIndex(new THREE.BufferAttribute(idx, 1));
  geo.computeVertexNormals();
  geo.computeBoundingSphere();

  // テクスチャ（草・水のシェーダーが参照）
  const hdata = new Uint16Array(W * W);
  for (let k = 0; k < W * W; k++) hdata[k] = THREE.DataUtils.toHalfFloat(hf.h[k]);
  const heightTex = new THREE.DataTexture(hdata, W, W, THREE.RedFormat, THREE.HalfFloatType);
  heightTex.magFilter = heightTex.minFilter = THREE.LinearFilter;
  heightTex.needsUpdate = true;

  const cdata = new Uint8Array(W * W * 4);
  const lin2srgb = (x) => Math.round(255 * Math.min(1, Math.pow(Math.max(0, x), 1 / 2.2)));
  for (let k = 0; k < W * W; k++) {
    cdata[k * 4] = lin2srgb(colors[k * 3]);
    cdata[k * 4 + 1] = lin2srgb(colors[k * 3 + 1]);
    cdata[k * 4 + 2] = lin2srgb(colors[k * 3 + 2]);
    cdata[k * 4 + 3] = 255;
  }
  const colorTex = new THREE.DataTexture(cdata, W, W, THREE.RGBAFormat);
  colorTex.colorSpace = THREE.SRGBColorSpace;
  colorTex.magFilter = colorTex.minFilter = THREE.LinearFilter;
  colorTex.needsUpdate = true;

  const shared = sharedIn || {
    uTime: { value: 0 },
    uDay: { value: 1 },
    uWind: { value: new THREE.Vector2(0.8, 0.6) },
  };

  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.96, metalness: 0 });
  const gt = groundTextures();
  const bio = BIOME[biome] ?? 0;
  mat.customProgramCacheKey = () => 'terrain-gt-' + bio;
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, shared);
    sh.uniforms.uGA = { value: gt.a };
    sh.uniforms.uGN = { value: gt.n };
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWPos;\nvarying vec3 vWNrm;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvWNrm = normalize(mat3(modelMatrix) * objectNormal);');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vWPos;\nvarying vec3 vWNrm;\nuniform float uTime, uDay;\nuniform vec2 uWind;\nuniform highp sampler2DArray uGA, uGN;\nvec3 gGroundN = vec3(0.0);\n#define BIOME ${bio}\n${NOISE}
        // 手描きテクスチャ：同じ絵の大きさ違いを重ねて、くり返しを目立たなくする（平均がおよそ 1）
        vec3 gTex(float L, vec2 uv) {
          vec3 a = texture(uGA, vec3(uv, L)).rgb;
          vec3 b = texture(uGA, vec3(uv * 0.23 + 0.37, L)).rgb;
          return a * 2.0 * mix(vec3(1.0), b * 2.0, 0.45);
        }
        vec3 gNrm(float L, vec2 uv) {
          vec3 a = texture(uGN, vec3(uv, L)).xyz * 2.0 - 1.0;
          vec3 b = texture(uGN, vec3(uv * 0.23 + 0.37, L)).xyz * 2.0 - 1.0;
          return vec3(a.xy + b.xy * 0.5, a.z);
        }`)
      .replace('#include <color_fragment>', /* glsl */`
        #include <color_fragment>
        vec2 wp = vWPos.xz;
        // --- 地面の種類の重み（Blender で塗った場所の色から） ---
        vec3 vc = diffuseColor.rgb;
        float mnc = min(vc.r, min(vc.g, vc.b));
        float lumc = dot(vc, vec3(0.3, 0.59, 0.11));
        float wSnow = max(smoothstep(0.45, 0.7, mnc), smoothstep(0.12, 0.3, vc.b - vc.r));
        float wGrass = smoothstep(0.0, 0.04, vc.g - max(vc.r, vc.b)) * (1.0 - wSnow);
        float wSand = smoothstep(0.32, 0.5, vc.r) * smoothstep(0.2, 0.35, vc.g) * (1.0 - wSnow) * (1.0 - wGrass);
        float wDark = smoothstep(0.05, 0.015, lumc) * (1.0 - wSand) * (1.0 - wGrass);
        float wDirt = max(0.0, 1.0 - wSnow - wGrass - wSand - wDark);
        float g2 = smoothstep(0.3, 0.16, vc.g) * 0.8 + smoothstep(0.55, 0.8, fbm3(wp * 0.03)) * 0.2;
        #if BIOME == 3
          float darkL = 5.0;
        #else
          float darkL = 2.0;
        #endif
        vec3 tex = vec3(0.0);
        vec3 gn = vec3(0.0);
        if (wGrass > 0.001) {
          vec2 uv = wp / 3.2;
          vec3 t = mix(gTex(0.0, uv), gTex(1.0, uv * 1.1), g2);
          tex += t * wGrass;
          gn += mix(gNrm(0.0, uv), gNrm(1.0, uv * 1.1), g2) * wGrass;
        }
        if (wDirt > 0.001) { vec2 uv = wp / 3.6; tex += gTex(2.0, uv) * wDirt; gn += gNrm(2.0, uv) * wDirt; }
        if (wSand > 0.001) { vec2 uv = wp / 4.6; tex += gTex(3.0, uv) * wSand; gn += gNrm(3.0, uv) * wSand; }
        if (wSnow > 0.001) { vec2 uv = wp / 5.0; tex += gTex(4.0, uv) * wSnow; gn += gNrm(4.0, uv) * wSnow; }
        if (wDark > 0.001) { vec2 uv = wp / 4.0; tex += gTex(darkL, uv) * wDark; gn += gNrm(darkL, uv) * wDark; }
        diffuseColor.rgb = vc * tex;
        gGroundN = gn;
        // 草地：ところどころ日なたっぽく明るい黄緑（大きなまだら）
        float n3 = fbm3(wp * 0.035);
        float lush = smoothstep(0.5, 0.78, n3);
        diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(1.1, 1.07, 0.78), lush * wGrass * 0.55);
        diffuseColor.rgb *= 0.93 + 0.14 * n3;
        // 急斜面は岩肌（三平面投影の岩のかたまりと地層）。雪の積もった所は残す
        float steep = 1.0 - smoothstep(0.55, 0.86, vWNrm.y);
        if (steep > 0.01) {
          vec3 an = abs(vWNrm);
          vec2 tp = an.x > an.z ? vWPos.zy : vWPos.xy;
          float f1 = fbm3(tp * 0.22);
          // 岩肌の手描きテクスチャ（横から 2 方向の投影）。色はその場所の色に寄せる
          vec3 rt = gTex(6.0, tp / 6.0);
          vec3 rockBase = mix(vec3(0.4, 0.38, 0.36), vc * 1.15 + 0.03, 0.62);
          vec3 rockC = rockBase * rt;
          rockC = mix(rockC, rockC * vec3(0.85, 0.95, 0.75), smoothstep(0.6, 0.8, f1) * 0.4);
          float snowy = wSnow;
          diffuseColor.rgb = mix(diffuseColor.rgb, rockC, steep * 0.92 * (1.0 - snowy * 0.75));
        }
        // 濡れた砂浜
        float wet = smoothstep(0.9, 0.15, vWPos.y);
        diffuseColor.rgb *= 1.0 - wet * 0.35;
        // 雲の影
        float cs = smoothstep(0.52, 0.8, fbm3(wp * 0.0042 + uWind * uTime * 0.006));
        diffuseColor.rgb *= 1.0 - cs * 0.38 * uDay;
      `)
      .replace('#include <normal_fragment_maps>', /* glsl */`
        #include <normal_fragment_maps>
        {
          // 地面の凹凸：テクスチャの法線（真上から貼っているので x→x、y→z）
          float stp = 1.0 - smoothstep(0.55, 0.86, vWNrm.y);
          vec3 bump = vec3(gGroundN.x, 0.0, -gGroundN.y) * 0.9 * (1.0 - stp);
          if (stp > 0.01) {
            vec3 an = abs(vWNrm);
            vec2 tp = an.x > an.z ? vWPos.zy : vWPos.xy;
            vec3 rn = gNrm(6.0, tp / 6.0);
            vec3 side = an.x > an.z ? vec3(0.0, rn.y, rn.x) : vec3(rn.x, rn.y, 0.0);
            bump += side * 1.4 * stp;
          }
          normal = normalize(normal + (viewMatrix * vec4(bump, 0.0)).xyz);
        }
      `)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>\nroughnessFactor = mix(roughnessFactor, 0.35, smoothstep(0.7, 0.1, vWPos.y));`);
  };

  const mesh = new THREE.Mesh(geo, mat);
  mesh.name = 'Terrain';
  mesh.receiveShadow = true;
  mesh.castShadow = false;
  return { mesh, heightTex, colorTex, colors, shared };
}
