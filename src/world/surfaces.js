import * as THREE from 'three';
import { NOISE } from './glsl.js';

/** ダンジョンでカメラと勇者の間の壁を切り抜くための共有 uniform */
export const CUT = {
  uCutCam: { value: new THREE.Vector3() },
  uCutTarget: { value: new THREE.Vector3() },
  uCutOn: { value: 0 },
  uCutR: { value: 3.2 },      // カメラ→注目点の線からこの距離までの壁を消す
  uCutNear: { value: 1.6 },   // カメラのすぐ近くの壁も消す
  uCutTop: { value: 0 },      // 注目点よりこれ以上高い所を近くだけ消す（0 で無効）
};

/**
 * Blender から来た単色マテリアルに、ワールド座標で貼る PBR テクスチャ（scripts/gen_textures.py で生成）を足す。
 *   色（平均 0.5 → マテリアル色に ×2）、法線（凹凸）、R=AO / G=粗さ
 * UV なしで貼れるよう、面の向きで 3 方向から投影して混ぜる（屋根は横 2 方向だけ・段は水平）。
 */
const TEX = {
  stone: { size: 3.6, normal: 0.85, ao: 0.55 },
  flagstone: { size: 3.0, normal: 1.0 },
  roof: { size: 2.0, normal: 1.0, sides: true },
  wood: { size: 1.0, normal: 0.8 },
  planks: { size: 2.0, normal: 0.9 },
  plaster: { size: 2.5, normal: 0.9 },
  rock: { size: 5.0, normal: 1.0 },
  fabric: { size: 0.6, normal: 0.7 },
};
let texLo = false;
/** 軽量設定では半分の解像度のテクスチャを使う */
export function setTextureQuality(lo) { texLo = lo; }
const texCache = {};
function texSet(kind) {
  if (texCache[kind]) return texCache[kind];
  const L = new THREE.TextureLoader();
  const base = `${import.meta.env.BASE_URL}assets/tex/${texLo ? 'lo/' : ''}${kind}`;
  const load = (suf, srgb) => {
    const t = L.load(`${base}_${suf}.jpg`);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = 8;
    return t;
  };
  return (texCache[kind] = { a: load('a', true), n: load('n', false), m: load('m', false) });
}

// 3 方向投影（ホワイトアウト合成で法線も混ぜる）。roof は X/Z の 2 方向だけ
const TRIPLANAR = (sides) => /* glsl */`
    vec3 tpN = normalize(vN);
    vec3 tpW = pow(abs(tpN), vec3(4.0));
    ${sides ? 'tpW.y = 0.0; tpW += vec3(1e-4, 0.0, 1e-4);' : ''}
    tpW /= (tpW.x + tpW.y + tpW.z);
    vec3 tpP = vW / uTexS;
    vec2 uvX = tpP.zy, uvY = tpP.xz, uvZ = tpP.xy;
    vec3 tpS = sign(tpN);
    uvX.x *= tpS.x; uvY.x *= tpS.y; uvZ.x *= -tpS.z;
    vec3 tA = texture2D(uTexA, uvX).rgb * tpW.x + texture2D(uTexA, uvY).rgb * tpW.y + texture2D(uTexA, uvZ).rgb * tpW.z;
    vec3 tM = texture2D(uTexM, uvX).rgb * tpW.x + texture2D(uTexM, uvY).rgb * tpW.y + texture2D(uTexM, uvZ).rgb * tpW.z;
    vec3 nX = texture2D(uTexN, uvX).xyz * 2.0 - 1.0;
    vec3 nY = texture2D(uTexN, uvY).xyz * 2.0 - 1.0;
    vec3 nZ = texture2D(uTexN, uvZ).xyz * 2.0 - 1.0;
    nX.x *= tpS.x; nY.x *= tpS.y; nZ.x *= -tpS.z;
    nX.xy *= uTexNS; nY.xy *= uTexNS; nZ.xy *= uTexNS;
    nX = vec3(nX.xy + tpN.zy, abs(nX.z) * tpN.x);
    nY = vec3(nY.xy + tpN.xz, abs(nY.z) * tpN.y);
    nZ = vec3(nZ.xy + tpN.xy, abs(nZ.z) * tpN.z);
    tpWN = normalize(nX.zyx * tpW.x + nY.xzy * tpW.y + nZ.xyz * tpW.z);
    diffuseColor.rgb *= tA * 2.0;
    diffuseColor.rgb *= mix(1.0, tM.r, uTexAO);
    vRough = tM.g / 0.85;
`;

// テクスチャのあとに足す、場所に応じた汚れ（地面ぎわ・雨だれ）
const EXTRA = {
  stone: /* glsl */`
    float lowDirt = smoothstep(2.5, 0.0, vW.y - uGround(vW));
    float grime = fbm3(vW.xz * 0.15 + vW.y * 0.05);
    diffuseColor.rgb *= 1.0 - grime * 0.18;
    diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(0.72, 0.76, 0.58), lowDirt * 0.5);
  `,
  plaster: /* glsl */`
    float low = smoothstep(1.4, 0.0, vW.y - uGround(vW));
    diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(0.7, 0.66, 0.56), low * 0.45);
    diffuseColor.rgb *= 0.94 + 0.08 * fbm3(vW.xy * 0.2 + vW.zx * 0.2);
  `,
  roof: /* glsl */`
    diffuseColor.rgb *= 0.88 + 0.2 * fbm3(vW.xz * 0.12);
  `,
  rock: /* glsl */`
    float moss = smoothstep(0.55, 0.75, fbm3(vW.xz * 0.3 + 3.0)) * smoothstep(1.6, 0.0, vW.y) * step(0.5, tpN.y + 0.6);
    diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.16, 0.24, 0.12), moss * 0.4);
  `,
};

const CUT_GLSL = /* glsl */`
    if (uCutOn > 0.5 && vW.y > 0.35) {
      vec3 ab = uCutTarget - uCutCam;
      float tt = clamp(dot(vW - uCutCam, ab) / dot(ab, ab), 0.0, 1.0);
      float dd = length(vW - (uCutCam + ab * tt));
      // 規則的なディザ（ノイズより半透明らしく見える）
      ivec2 bi = ivec2(mod(gl_FragCoord.xy, 4.0));
      float dith = (float[16](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.)[bi.x + bi.y * 4] + 0.5) / 16.0;
      float kc = max(step(tt, 0.96) * smoothstep(uCutR, uCutR - 1.2, dd), smoothstep(uCutNear, uCutNear - 1.0, length(vW - uCutCam)));
      // 勇者のまわりの高い壁（見下ろすカメラの邪魔）も上から削る
      if (uCutTop > 0.0) kc = max(kc, smoothstep(uCutTop, uCutTop + 0.8, vW.y - uCutTarget.y) * smoothstep(13.0, 9.0, length(vW.xz - uCutTarget.xz)));
      if (dith < kc) discard;
    }
`;

function kindOf(name) {
  if (/^(StoneFloor|SandFloor|ChaosFloor)$/.test(name)) return 'flagstone';
  if (/^(Stone|StoneDark|TowerStone|PyrStone|PyrStoneDark|SmithStone|SmithStoneDark|ChaosStone|ChaosStoneDark)$/.test(name)) return 'stone';
  if (/^(CaveRock|CaveRockDark|CaveFloor)$/.test(name)) return 'rock';
  if (/^Roof|TowerRoof/.test(name)) return 'roof';
  if (name === 'WoodFloor') return 'planks';
  if (/^(Wood|WoodDark|Bark|Door|LogWood|LogWoodDark)$/.test(name) || /^Shutter/.test(name)) return 'wood';
  if (/^(Plaster|Adobe|AdobeDark)$/.test(name)) return 'plaster';
  if (/^(Carpet|TowerCarpet|RoyalCarpet|ChaosCarpet)$/.test(name)) return 'fabric';
  return null;
}

export function enhanceSurface(mat, heightTex, uvParams, cut = false, offU = null) {
  const off = offU || { value: new THREE.Vector2() };
  const kind = kindOf(mat.name || '') || (cut ? 'none' : null);
  if (!kind || mat.userData.enhanced) return;
  mat.userData.enhanced = true;
  const T = TEX[kind];
  const tex = T ? texSet(kind) : null;
  if (kind === 'stone') mat.color.multiplyScalar(0.85);
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uHeightT = { value: heightTex };
    sh.uniforms.uHFp = { value: uvParams };
    sh.uniforms.uHFo = off;
    if (tex) {
      sh.uniforms.uTexA = { value: tex.a };
      sh.uniforms.uTexN = { value: tex.n };
      sh.uniforms.uTexM = { value: tex.m };
      sh.uniforms.uTexS = { value: T.size };
      sh.uniforms.uTexNS = { value: T.normal };
      sh.uniforms.uTexAO = { value: T.ao ?? 0.85 };
    }
    if (cut) Object.assign(sh.uniforms, CUT);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vW;\nvarying vec3 vN;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvW = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvN = normalize(mat3(modelMatrix) * objectNormal);');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vW;\nvarying vec3 vN;\nfloat vRough = 1.0;\nvec3 tpWN = vec3(0.0);\n${NOISE}\nuniform sampler2D uHeightT;
uniform vec4 uHFp;
uniform vec2 uHFo;
uniform sampler2D uTexA, uTexN, uTexM;
uniform float uTexS, uTexNS, uTexAO;
float uGround(vec3 p) { return texture2D(uHeightT, ((p.xz - uHFo + uHFp.x) / uHFp.y + 0.5) / uHFp.z).r; }`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n${cut ? CUT_GLSL : ''}\n${tex ? TRIPLANAR(T.sides) : ''}\n${tex ? (EXTRA[kind] || '') : ''}`)
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor *= vRough;')
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>\n${tex ? 'normal = normalize((viewMatrix * vec4(tpWN, 0.0)).xyz);' : ''}`);
    if (cut) sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform vec3 uCutCam;\nuniform vec3 uCutTarget;\nuniform float uCutOn;\nuniform float uCutR;\nuniform float uCutNear;\nuniform float uCutTop;');
  };
  mat.customProgramCacheKey = () => 'surface2-' + kind + (cut ? '-cut' : '');
  mat.needsUpdate = true;
}
