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
 * Blender から来た単色マテリアルに、ワールド座標ベースのプロシージャル模様を足す。
 *  石：石積み（目地・石ごとの色むら・汚れ）、屋根：瓦の段、木：木目、漆喰：ムラ
 */
const PATTERNS = {
  stone: /* glsl */`
    vec3 ap = abs(vN);
    vec2 uv = ap.y > 0.7 ? vW.xz : (ap.x > ap.z ? vW.zy : vW.xy);
    float rowH = 0.55;
    float row = floor(uv.y / rowH);
    float bx = uv.x / 1.1 + (mod(row, 2.0) * 0.5);
    vec2 cell = vec2(floor(bx), row);
    vec2 f = vec2(fract(bx), fract(uv.y / rowH));
    float mortar = smoothstep(0.0, 0.035, f.x) * smoothstep(1.0, 0.965, f.x) * smoothstep(0.0, 0.07, f.y) * smoothstep(1.0, 0.93, f.y);
    if (ap.y > 0.7) mortar = mix(mortar, 1.0, 0.6);
    float var = h21(cell) - 0.5;
    float grime = fbm3(vW.xz * 0.15 + vW.y * 0.05);
    float lowDirt = smoothstep(2.5, 0.0, vW.y - uGround(vW));
    vec3 c = diffuseColor.rgb * (0.86 + var * 0.22) * (0.8 + 0.35 * vnoise(uv * 3.0));
    c = mix(c * 0.45, c, mortar);
    c *= 1.0 - grime * 0.25;
    c = mix(c, c * vec3(0.75, 0.78, 0.6), lowDirt * 0.55);
    diffuseColor.rgb = c;
    vRough = mix(1.0, 0.85, mortar);
  `,
  roof: /* glsl */`
    float rows = vW.y / 0.32;
    float r = floor(rows);
    float fx = (vW.x + vW.z) / 0.42 + mod(r, 2.0) * 0.5;
    float fr = fract(rows);
    float tile = smoothstep(0.0, 0.12, fr) * (0.75 + 0.25 * fr);
    float edge = smoothstep(0.0, 0.08, fract(fx)) * smoothstep(1.0, 0.92, fract(fx));
    float var = h21(vec2(floor(fx), r)) - 0.5;
    vec3 c = diffuseColor.rgb * (0.85 + var * 0.25);
    c *= mix(0.55, 1.0, tile) * mix(0.75, 1.0, edge);
    c *= 0.85 + 0.25 * vnoise(vW.xz * 0.7);
    diffuseColor.rgb = c;
    vRough = 0.6 + 0.3 * (1.0 - tile);
  `,
  wood: /* glsl */`
    vec3 ap = abs(vN);
    float along = ap.y > 0.7 ? vW.x : vW.y;
    float grain = sin((vW.x + vW.z) * 9.0 + vnoise(vec2(along * 0.6, vW.x + vW.z) * 2.0) * 6.0) * 0.5 + 0.5;
    diffuseColor.rgb *= 0.78 + grain * 0.22 + (vnoise(vW.xy * 4.0 + vW.zz) - 0.5) * 0.15;
    vRough = 0.85;
  `,
  rock: /* glsl */`
    vec3 ap = abs(vN);
    vec2 uv = ap.y > 0.7 ? vW.xz : (ap.x > ap.z ? vW.zy : vW.xy);
    float f1 = fbm3(uv * 0.35), f2 = vnoise(uv * 2.2), f3 = vnoise(uv * 7.0);
    float strata = sin(vW.y * 2.3 + f1 * 6.0) * 0.5 + 0.5;
    vec3 c = diffuseColor.rgb * (0.7 + f1 * 0.45) * (0.85 + f2 * 0.25) * (0.92 + f3 * 0.12);
    c *= 0.85 + strata * 0.2;
    // しめった筋と、床のあたりの苔
    float wet = smoothstep(0.62, 0.8, vnoise(vec2(uv.x * 1.5, vW.y * 0.15)));
    c = mix(c, c * 0.6, wet * (ap.y < 0.7 ? 1.0 : 0.0));
    float moss = smoothstep(0.55, 0.75, fbm3(uv * 0.6 + 3.0)) * smoothstep(1.6, 0.0, vW.y) ;
    c = mix(c, vec3(0.16, 0.24, 0.12), moss * 0.5);
    diffuseColor.rgb = c;
    vRough = mix(1.0, 0.45, wet);
  `,
  fabric: /* glsl */`
    vec2 uv = vW.xz;
    float weave = sin(uv.x * 60.0) * sin(uv.y * 60.0) * 0.5 + 0.5;
    float n = fbm3(uv * 1.5);
    vec3 c = diffuseColor.rgb * (0.8 + n * 0.3) * (0.93 + weave * 0.08);
    // ふちの金色の模様
    vec2 f = fract(uv / 2.0);
    float edge = step(0.92, max(abs(f.x - 0.5), abs(f.y - 0.5)) * 2.0);
    diffuseColor.rgb = c;
    vRough = 1.0;
  `,
  planks: /* glsl */`
    float pw = 0.28;
    float row = floor(vW.z / pw);
    float len = 1.6 + h21(vec2(row, 3.1)) * 1.2;
    float px = vW.x / len + h21(vec2(row, 7.7));
    float col = floor(px);
    vec2 f = vec2(fract(px), fract(vW.z / pw));
    float gap = smoothstep(0.0, 0.045, f.y) * smoothstep(1.0, 0.955, f.y) * smoothstep(0.0, 0.012, f.x) * smoothstep(1.0, 0.988, f.x);
    float var = h21(vec2(col, row)) - 0.5;
    float grain = vnoise(vec2(vW.x * 1.2, vW.z * 26.0 + row * 13.0)) * 0.6 + vnoise(vec2(vW.x * 4.0, vW.z * 60.0)) * 0.4;
    float knot = smoothstep(0.08, 0.0, length(vec2(fract(px * 2.3 + row) - 0.5, (f.y - 0.5) * 0.35))) * step(0.7, h21(vec2(col * 1.3, row)));
    vec3 c = diffuseColor.rgb * (0.9 + var * 0.35) * (0.82 + grain * 0.3);
    c *= 1.0 - knot * 0.45;
    c = mix(c * 0.35, c, gap);
    diffuseColor.rgb = c;
    vRough = mix(0.95, 0.55, gap);
  `,
  none: '',
  plaster: /* glsl */`
    float n = fbm3(vW.xy * 0.8 + vW.zx * 0.8);
    float stain = smoothstep(0.55, 0.85, fbm3(vec2(vW.x + vW.z, vW.y * 2.5) * 0.35));
    diffuseColor.rgb *= 0.9 + n * 0.14;
    diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(0.82, 0.78, 0.7), stain * 0.5);
    float low = smoothstep(1.4, 0.0, vW.y - uGround(vW));
    diffuseColor.rgb *= 1.0 - low * 0.25;
    vRough = 0.95;
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
  if (/^(Stone|StoneDark|TowerStone|StoneFloor)$/.test(name)) return 'stone';
  if (/^(CaveRock|CaveRockDark|CaveFloor)$/.test(name)) return 'rock';
  if (/^Roof|TowerRoof/.test(name)) return 'roof';
  if (name === 'WoodFloor') return 'planks';
  if (/^(Wood|WoodDark|Bark|Door)$/.test(name)) return 'wood';
  if (/^Plaster$/.test(name)) return 'plaster';
  if (/^(Carpet|TowerCarpet)$/.test(name)) return 'fabric';
  return null;
}

export function enhanceSurface(mat, heightTex, uvParams, cut = false) {
  const kind = kindOf(mat.name || '') || (cut ? 'none' : null);
  if (!kind || mat.userData.enhanced) return;
  mat.userData.enhanced = true;
  if (kind === 'stone') mat.color.multiplyScalar(0.78);
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uHeightT = { value: heightTex };
    sh.uniforms.uHFp = { value: uvParams };
    if (cut) Object.assign(sh.uniforms, CUT);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vW;\nvarying vec3 vN;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvW = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvN = normalize(mat3(modelMatrix) * objectNormal);');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vW;\nvarying vec3 vN;\nfloat vRough = 1.0;\n${NOISE}\nuniform sampler2D uHeightT;
uniform vec4 uHFp;
float uGround(vec3 p) { return texture2D(uHeightT, ((p.xz + uHFp.x) / uHFp.y + 0.5) / uHFp.z).r; }`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n${cut ? CUT_GLSL : ''}\n${PATTERNS[kind]}`)
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor *= vRough;');
    if (cut) sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform vec3 uCutCam;\nuniform vec3 uCutTarget;\nuniform float uCutOn;\nuniform float uCutR;\nuniform float uCutNear;\nuniform float uCutTop;');
  };
  mat.customProgramCacheKey = () => 'surface-' + kind + (cut ? '-cut' : '');
  mat.needsUpdate = true;
}
