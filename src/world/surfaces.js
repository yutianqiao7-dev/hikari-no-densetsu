import { NOISE } from './glsl.js';

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

function kindOf(name) {
  if (/^(Stone|StoneDark|TowerStone)$/.test(name)) return 'stone';
  if (/^Roof|TowerRoof/.test(name)) return 'roof';
  if (/^(Wood|WoodDark|Bark|Door)$/.test(name)) return 'wood';
  if (/^Plaster$/.test(name)) return 'plaster';
  return null;
}

export function enhanceSurface(mat, heightTex, uvParams) {
  const kind = kindOf(mat.name || '');
  if (!kind || mat.userData.enhanced) return;
  mat.userData.enhanced = true;
  if (kind === 'stone') mat.color.multiplyScalar(0.78);
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uHeightT = { value: heightTex };
    sh.uniforms.uHFp = { value: uvParams };
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vW;\nvarying vec3 vN;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvW = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvN = normalize(mat3(modelMatrix) * objectNormal);');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vW;\nvarying vec3 vN;\nfloat vRough = 1.0;\n${NOISE}\nuniform sampler2D uHeightT;
uniform vec4 uHFp;
float uGround(vec3 p) { return texture2D(uHeightT, ((p.xz + uHFp.x) / uHFp.y + 0.5) / uHFp.z).r; }`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n${PATTERNS[kind]}`)
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor *= vRough;');
  };
  mat.customProgramCacheKey = () => 'surface-' + kind;
  mat.needsUpdate = true;
}
