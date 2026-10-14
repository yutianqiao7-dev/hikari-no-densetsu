import * as THREE from 'three';
import { NOISE } from './glsl.js';

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
export function buildTerrain(hf, gltfTerrainMesh, sharedIn = null) {
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
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, shared);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWPos;\nvarying vec3 vWNrm;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvWNrm = normalize(mat3(modelMatrix) * objectNormal);');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vWPos;\nvarying vec3 vWNrm;\nuniform float uTime, uDay;\nuniform vec2 uWind;\n${NOISE}`)
      .replace('#include <color_fragment>', /* glsl */`
        #include <color_fragment>
        vec2 wp = vWPos.xz;
        float n1 = vnoise(wp * 0.45), n2 = vnoise(wp * 2.3), n3 = fbm3(wp * 0.035);
        float detail = 0.80 + 0.24 * n1 + 0.10 * n2 + 0.14 * (n3 - 0.5);
        diffuseColor.rgb *= detail;
        float lush = smoothstep(0.5, 0.78, n3);
        float isGrass = smoothstep(0.0, 0.06, diffuseColor.g - max(diffuseColor.r, diffuseColor.b));
        diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(1.12, 1.08, 0.72), lush * isGrass * 0.6);
        float tgl = dot(diffuseColor.rgb, vec3(0.3, 0.59, 0.11));
        diffuseColor.rgb = mix(diffuseColor.rgb, mix(vec3(tgl), diffuseColor.rgb, 0.74) * vec3(1.04, 0.98, 0.84), isGrass);
        // 土の道：小石・湿ったまだら
        float dirt = smoothstep(0.0, 0.06, diffuseColor.r - diffuseColor.g) * (1.0 - smoothstep(0.55, 0.8, diffuseColor.b / max(diffuseColor.r, 0.01)));
        if (dirt > 0.01) {
          float peb = smoothstep(0.86, 0.93, vnoise(wp * 16.0)) * smoothstep(0.3, 0.6, vnoise(wp * 2.0));
          float peb2 = smoothstep(0.86, 0.92, vnoise(wp * 23.0 + 7.0));
          float damp = smoothstep(0.45, 0.75, fbm3(wp * 0.25));
          float grain = vnoise(wp * 7.0) * 0.5 + vnoise(wp * 31.0) * 0.5;
          vec3 dc = diffuseColor.rgb * (1.0 - damp * 0.2) * (0.88 + grain * 0.2);
          dc = mix(dc, dc * 1.35 + 0.03, peb * 0.55);
          dc = mix(dc, dc * 0.6, peb2 * 0.45);
          diffuseColor.rgb = mix(diffuseColor.rgb, dc, dirt);
        }
        // 急斜面は岩肌（三平面投影の岩のかたまりと地層）。雪の積もった所は残す
        float steep = 1.0 - smoothstep(0.55, 0.86, vWNrm.y);
        if (steep > 0.01) {
          vec3 an = abs(vWNrm);
          vec2 tp = an.x > an.z ? vWPos.zy : vWPos.xy;
          float f1 = fbm3(tp * 0.22), f2 = fbm3(tp * 0.9 + 4.0), f3 = vnoise(tp * 3.7);
          float strata = sin(vWPos.y * 1.6 + f1 * 7.0) * 0.5 + 0.5;
          vec3 rockC = mix(vec3(0.28, 0.26, 0.25), vec3(0.56, 0.52, 0.47), strata * 0.45 + f2 * 0.55) * (0.82 + f3 * 0.32);
          // 砂・雪・火山岩など、その場所の色に寄せた岩肌にする
          vec3 tintC = diffuseColor.rgb * (0.72 + 0.55 * (strata * 0.45 + f2 * 0.55)) * (0.85 + f3 * 0.3);
          rockC = mix(rockC, tintC, 0.72);
          rockC = mix(rockC, rockC * vec3(0.85, 0.95, 0.75), smoothstep(0.6, 0.8, f1) * 0.5);
          float snowy = smoothstep(0.62, 0.8, min(diffuseColor.r, diffuseColor.b));
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
          vec2 wq = vWPos.xz * 1.3;
          float e = 0.08;
          float b0 = vnoise(wq), bx = vnoise(wq + vec2(e, 0.0)), bz = vnoise(wq + vec2(0.0, e));
          vec3 bump = vec3(b0 - bx, 0.0, b0 - bz) * 2.2;
          float stp = 1.0 - smoothstep(0.55, 0.86, vWNrm.y);
          if (stp > 0.01) {
            vec2 rq = vWPos.xy * 0.5 + vWPos.zy * 0.5;
            float r0 = fbm3(rq), rx = fbm3(rq + vec2(0.06, 0.0)), ry = fbm3(rq + vec2(0.0, 0.06));
            bump += vec3(r0 - rx, (r0 - ry) * 0.5, r0 - ry) * 9.0 * stp;
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
