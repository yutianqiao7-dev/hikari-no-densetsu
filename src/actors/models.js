import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

/**
 * キャラの素材の細かな質感（scripts/gen_textures.py の布・革・金属・髪・肌）。
 * 動いてもずれないよう、骨格の初期姿勢の座標で 3 方向から貼り、凹凸は画面上の高さの変化から作る。
 */
const DETAIL = {
  cloth: { size: 0.12, bump: 0.6, alb: 0.55 },
  leather: { size: 0.25, bump: 0.8, alb: 0.6 },
  metal: { size: 0.5, bump: 0.7, alb: 0.5 },
  hair: { size: 0.09, bump: 0.9, alb: 0.75 },
  skin: { size: 0.08, bump: 0.25, alb: 0.25 },
};
const detailTex = {};
function detailSet(kind) {
  if (detailTex[kind]) return detailTex[kind];
  const L = new THREE.TextureLoader();
  const base = `${import.meta.env.BASE_URL}assets/tex/${kind}`;
  const load = (suf, srgb) => {
    const t = L.load(`${base}_${suf}.jpg`);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = 8;
    return t;
  };
  return (detailTex[kind] = { a: load('a', true), m: load('m', false) });
}

function addDetail(mat, kind) {
  const D = DETAIL[kind];
  const tex = detailSet(kind);
  const prev = mat.onBeforeCompile;
  mat.onBeforeCompile = (sh, r) => {
    if (prev) prev(sh, r);
    sh.uniforms.uDtA = { value: tex.a };
    sh.uniforms.uDtM = { value: tex.m };
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vBP;\nvarying vec3 vBN;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvBP = position;\nvBN = normal;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
varying vec3 vBP;
varying vec3 vBN;
uniform sampler2D uDtA, uDtM;
float dtH = 0.0;
vec3 dtPerturb(vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float fd) {
  vec3 sx = normalize(dFdx(surf_pos)), sy = normalize(dFdy(surf_pos));
  vec3 r1 = cross(sy, surf_norm), r2 = cross(surf_norm, sx);
  float det = dot(sx, r1) * fd;
  vec3 g = sign(det) * (dHdxy.x * r1 + dHdxy.y * r2);
  return normalize(abs(det) * surf_norm - g);
}`)
      .replace('#include <color_fragment>', `#include <color_fragment>
{
  vec3 n = normalize(vBN);
  vec3 w = pow(abs(n), vec3(4.0)); w /= (w.x + w.y + w.z);
  vec3 p = vBP / ${D.size.toFixed(3)};
  vec3 a = texture2D(uDtA, p.zy).rgb * w.x + texture2D(uDtA, p.xz).rgb * w.y + texture2D(uDtA, p.xy).rgb * w.z;
  vec3 m = texture2D(uDtM, p.zy).rgb * w.x + texture2D(uDtM, p.xz).rgb * w.y + texture2D(uDtM, p.xy).rgb * w.z;
  diffuseColor.rgb *= mix(vec3(1.0), a * 2.0, ${D.alb.toFixed(2)});
  diffuseColor.rgb *= mix(1.0, m.r, 0.5);
  dtH = m.b;
}`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
{
  float fade = smoothstep(14.0, 2.5, length(vViewPosition));
  vec2 dH = vec2(dFdx(dtH), dFdy(dtH)) * ${(D.bump * 0.02).toFixed(4)} * fade;
  normal = dtPerturb(-vViewPosition, normal, dH, faceDirection);
}`);
  };
  const key = (mat.customProgramCacheKey ? mat.customProgramCacheKey() : '') + '-dt-' + kind;
  mat.customProgramCacheKey = () => key;
  mat.needsUpdate = true;
}

// ---------------------------------------------------------------- トゥーン（ドラクエ8風のくっきりした陰と輪郭線）
// 2 段にするのは色（拡散光）だけ。つや（鏡面反射）を変えると影の面で値が極端に大きくなる
const LAMBERT = 'reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseContribution ) * ( 1.0 - F );';
const TOON_CHUNK = THREE.ShaderChunk.lights_physical_pars_fragment.replace(LAMBERT,
  'reflectedLight.directDiffuse += toonStep( toonNL( geometryNormal, dotNL ) ) * directLight.color * BRDF_Lambert( material.diffuseContribution ) * ( 1.0 - F );');
if (TOON_CHUNK === THREE.ShaderChunk.lights_physical_pars_fragment) console.warn('toon: chunk not patched');

/** キャラの陰を決める「決まった光」の向き（画面に対して左上・手前から）。いつも影の面がはっきり出る */
export const KEY_DIR = { value: new THREE.Vector3(-0.66, 0.5, 0.56).normalize() };

const TOON_FN = (char, soft) => /* glsl */`
uniform vec3 uKeyDir;
float toonStep(float x) {
  // 明るい面と影の面の 2 段（境目はごく細くぼかす）。明るい面の中にもうっすら段。肌は影を浅く
  return mix(${soft ? '0.5' : (char ? '0.2' : '0.28')}, 1.0, smoothstep(0.1, 0.14, x)) * (0.88 + 0.12 * smoothstep(0.5, 0.56, x));
}
float toonNL(vec3 n, float dl) {
  ${char ? 'return max(dot(n, uKeyDir), 0.0) * 0.75 + dl * 0.25;' : 'return dl;'}
}`;

// 縁の明るい線（リムライト）と、髪の天使の輪
const RIM = (hair) => /* glsl */`
{
  vec3 rN = normalize(normal);
  vec3 rV = normalize(vViewPosition);
  float ndv = saturate(dot(rN, rV));
  float rim = smoothstep(0.66, 0.72, 1.0 - ndv) * smoothstep(-0.3, 0.3, dot(rN, uKeyDir));
  totalEmissiveRadiance += diffuseColor.rgb * rim * 0.6 + vec3(rim * 0.05);
  ${hair ? `float band = smoothstep(0.1, 0.02, abs(rN.y - 0.42)) * smoothstep(0.35, 0.7, ndv);
  totalEmissiveRadiance += vec3(1.0, 0.96, 0.88) * band * 0.3 * (0.5 + dtH);` : ''}
}`;

/**
 * 光の当たり方を 2 段にする（金属のつや＝鏡面反射はそのまま）。
 * kind: 'world'（太陽どおり）/ 'char'（決まった光＋縁の線）/ 'hair'（さらに天使の輪）
 */
export function toonify(mat, kind = 'world') {
  if (!mat || mat.userData.toon || mat.isMeshBasicMaterial) return mat;
  mat.userData.toon = true;
  const char = kind !== 'world';
  const prev = mat.onBeforeCompile;
  const k0 = mat.customProgramCacheKey ? mat.customProgramCacheKey.call(mat) : '';
  mat.onBeforeCompile = (sh, r) => {
    if (prev) prev(sh, r);
    sh.uniforms.uKeyDir = KEY_DIR;
    sh.fragmentShader = sh.fragmentShader.replace('#include <lights_physical_pars_fragment>', TOON_FN(char, kind === 'skin') + '\n' + TOON_CHUNK);
    if (char) {
      sh.fragmentShader = sh.fragmentShader.replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' + RIM(kind === 'hair'));
      // Blender で焼いたすき間の陰（頂点の色）：少し強めて、くっきり
      sh.fragmentShader = sh.fragmentShader.replace('#include <color_fragment>', `#ifdef USE_COLOR
        diffuseColor.rgb *= mix(vec3(1.0), pow(clamp(vColor.rgb * 1.08, 0.0, 1.0), vec3(1.6)), ${kind === 'skin' ? '0.3' : '0.85'});
      #endif`);
    }
  };
  mat.customProgramCacheKey = () => k0 + '-toon-' + kind;
  mat.needsUpdate = true;
  return mat;
}

/** 輪郭線の太さ（画面上のピクセル）と画面の大きさ。毎フレーム main から更新する */
export const OUTLINE_PX = { value: 2.0 };
export const OUTLINE_RES = { value: new THREE.Vector2(1024, 640) };
const HIDE = new THREE.MeshBasicMaterial({ visible: false });

/** 輪郭線の色：もとの色を暗く、少し赤茶寄りに */
function outlineMat(base) {
  const c = base.color ? base.color.clone() : new THREE.Color(0.4, 0.4, 0.4);
  c.multiplyScalar(0.22).lerp(new THREE.Color(0.06, 0.035, 0.03), 0.5);
  const m = new THREE.MeshBasicMaterial({ color: c, side: THREE.BackSide });
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uOWpx = OUTLINE_PX;
    sh.uniforms.uRes = OUTLINE_RES;
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nuniform float uOWpx;\nuniform vec2 uRes;')
      .replace('#include <project_vertex>', `
        #ifdef USE_SKINNING
          vec3 olN = normalize(objectNormal);
        #else
          vec3 olN = normalize(normal);
        #endif
        transformed += olN * 0.0015;
        #include <project_vertex>
        // 画面の上で一定の太さに外へ押し出す（遠くでは少し細く）
        vec4 cn = projectionMatrix * vec4(normalize(normalMatrix * olN), 0.0);
        vec2 od = cn.xy;
        float ol = length(od);
        od = ol > 1e-5 ? od / ol : vec2(0.0);
        float px = uOWpx * clamp(9.0 / max(gl_Position.w, 0.1), 0.4, 1.0);
        gl_Position.xy += od * px * 2.0 / uRes * gl_Position.w;`);
  };
  m.customProgramCacheKey = () => 'outline2';
  m.userData.outline = true;
  return m;
}

/** 輪郭線：裏返した少し太いメッシュを重ねる（スキンメッシュは同じ骨で動かす） */
export function addOutlines(root, skip) {
  const list = [];
  root.traverse((o) => { if (o.isMesh && !o.userData.isOutline) list.push(o); });
  for (const o of list) {
    if (skip && skip.test(o.name)) continue;
    const src = Array.isArray(o.material) ? o.material : [o.material];
    if (src.every((m) => m.transparent || m.userData.noOutline)) continue;
    const oms = src.map((m) => (m.transparent || m.userData.noOutline ? HIDE : outlineMat(m)));
    const mm = Array.isArray(o.material) ? oms : oms[0];
    let ol;
    if (o.isSkinnedMesh) {
      ol = new THREE.SkinnedMesh(o.geometry, mm);
      ol.bind(o.skeleton, o.bindMatrix);
      ol.bindMode = o.bindMode;
      ol.position.copy(o.position);
      ol.quaternion.copy(o.quaternion);
      ol.scale.copy(o.scale);
      o.parent.add(ol);
    } else {
      ol = new THREE.Mesh(o.geometry, mm);
      o.add(ol);
    }
    ol.name = o.name + '_Outline';
    ol.userData.isOutline = true;
    ol.castShadow = false;
    ol.receiveShadow = false;
    ol.frustumCulled = false;
  }
}

function detailKind(n) {
  if (/_(hair|beard)$|Hair|Beard/i.test(n)) return 'hair';
  if (/_skin$|^Skin/i.test(n)) return 'skin';
  if (/_(boot|belt|glove)$|Leather|Strap|Boot|Belt|Glove/i.test(n)) return 'leather';
  if (/_metal$|Blade|Silver|Armor|Helmet|Iron|Steel/i.test(n)) return 'metal';
  if (/_(top|pants|robe|dress|Cape|Robe|Dress|apron|vest|Lining|hat|Band|hatband|sash|ribbon)$|Cape|Frill|Velvet|Cloth/i.test(n)) return 'cloth';
  return null;
}

/**
 * characters.glb の人型・モンスターを複製して使うためのライブラリ
 * - 人型は全員同じ骨格なので Hero のアニメーションを共有する
 * - 布にはシーン（布の光沢）、髪には異方性っぽいハイライトを付けて質感を上げる
 */
export class ModelLibrary {
  constructor(gltf) {
    this.templates = {};
    for (const child of gltf.scene.children) {
      this.templates[child.name] = child;
      // glTF ローダーは重複名に _1, _2 … を付けるので、骨の名前を元に戻してアニメーションを共有できるようにする
      child.traverse((o) => { if (o.isBone) o.name = o.name.replace(/_\d+$/, ''); });
    }
    this.clips = {};
    for (const c of gltf.animations) this.clips[c.name] = c;
    this._upgraded = new Map();
    for (const t of Object.values(this.templates)) this.upgradeMaterials(t);
    // 人型は顔の描いた部品を除いて輪郭線をつける（モンスターは複製したあとに）
    for (const [k, t] of Object.entries(this.templates)) {
      if (!/^Mon_/.test(k)) addOutlines(t, /_(Face|Eye[LR]|Blush[LR]|Lashes|MouthIn)$/);
    }
  }

  upgradeMaterials(root) {
    root.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.receiveShadow = true;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      const out = mats.map((m) => this.upgrade(m));
      o.material = Array.isArray(o.material) ? out : out[0];
    });
  }

  upgrade(m) {
    if (this._upgraded.has(m)) return this._upgraded.get(m);
    const n = m.name || '';
    let r = m;
    const fabric = /_(top|pants|robe|dress|Cape|Robe|Dress|apron|vest|Lining|hat|Band|hatband)$|Cape|Frill|Fur|Velvet/i.test(n);
    const hair = /_(hair|beard)$|Hair|Beard/i.test(n);
    const skin = /_skin$|^Skin/i.test(n);
    if (fabric || hair || skin) {
      const p = new THREE.MeshPhysicalMaterial();
      THREE.MeshStandardMaterial.prototype.copy.call(p, m);
      p.defines = { STANDARD: '', PHYSICAL: '' };
      p.name = n;
      if (fabric) {
        p.sheen = 1.0;
        p.sheenRoughness = 0.55;
        p.sheenColor = m.color.clone().lerp(new THREE.Color(1, 1, 1), 0.45);
        p.roughness = Math.max(0.75, m.roughness);
      }
      if (hair) {
        p.roughness = 0.42;
        p.sheen = 0.7;
        p.sheenRoughness = 0.3;
        p.sheenColor = m.color.clone().multiplyScalar(2.2);
        p.clearcoat = 0.25;
        p.clearcoatRoughness = 0.45;
      }
      if (skin) {
        p.roughness = 0.5;
        p.sheen = 0.5;
        p.sheenRoughness = 0.55;
        p.sheenColor = new THREE.Color(1.0, 0.5, 0.4);
        // 光が肌の中で散るような、ほんのりした赤み
        p.emissive = m.color.clone().multiply(new THREE.Color(0.06, 0.025, 0.018));
      }
      if (m.side === THREE.DoubleSide) p.side = THREE.DoubleSide;
      r = p;
    }
    if (/Blade|Silver|Armor|Gold|Sapphire|Ruby/i.test(n)) r.envMapIntensity = 1.6;
    const dk = detailKind(n);
    if (dk && !/^Mon_/.test(n)) addDetail(r, dk);
    toonify(r, /^Mon_/.test(n) ? 'char' : (dk === 'hair' ? 'hair' : (dk === 'skin' ? 'skin' : 'char')));
    if (/Eye|Iris|Pupil/i.test(n)) { r.roughness = 0.08; r.envMapIntensity = 1.4; }
    // 描いた目・ほお紅は肌の上に重ねる半透明の板
    if (/_EyeTex$|^Blush$/.test(n)) {
      r.transparent = true;
      r.depthWrite = false;
      r.polygonOffset = true;
      r.polygonOffsetFactor = -2;
      r.polygonOffsetUnits = -2;
      if (/Blush/.test(n)) { r.roughness = 0.8; r.envMapIntensity = 0; }
    }
    this._upgraded.set(m, r);
    return r;
  }

  has(name) { return !!this.templates[name]; }

  /** ぷるぷるのゼリー：透明感とつや */
  gelify(m) {
    const p = new THREE.MeshPhysicalMaterial();
    THREE.MeshStandardMaterial.prototype.copy.call(p, m);
    p.defines = { STANDARD: '', PHYSICAL: '' };
    p.roughness = 0.12;
    p.clearcoat = 1.0;
    p.clearcoatRoughness = 0.08;
    p.sheen = 0.5;
    p.sheenColor = m.color.clone().lerp(new THREE.Color(1, 1, 1), 0.6);
    p.emissive = m.color.clone().multiplyScalar(0.12);
    p.name = m.name;
    return p;
  }

  /** 人型キャラクター（スキンメッシュ） */
  humanoid(name) {
    const t = this.templates[name];
    const root = SkeletonUtils.clone(t);
    root.position.set(0, 0, 0);
    root.rotation.set(0, 0, 0);
    root.updateMatrixWorld(true);
    const mixer = new THREE.AnimationMixer(root);
    const actions = {};
    for (const [k, clip] of Object.entries(this.clips)) actions[k] = mixer.clipAction(clip);
    const parts = {};
    const byName = {};
    root.traverse((o) => {
      if (o.isMesh) o.frustumCulled = false;
      byName[o.name] = o;
      if (o !== root && o.name.startsWith(name + '_') && !o.userData.isOutline) {
        const key = o.name.slice(name.length + 1);
        if (!parts[key]) parts[key] = o;
      }
    });
    // 部品を隠したら輪郭線も隠す（剣と鞘の持ちかえなど）
    const outlinePairs = [];
    root.traverse((o) => { if (o.userData.isOutline && byName[o.name.replace(/_Outline$/, '')]) outlinePairs.push([byName[o.name.replace(/_Outline$/, '')], o]); });
    return { root, mixer, actions, parts, outlinePairs };
  }

  /** モンスター（部位ごとのオブジェクト） */
  monster(name, recolor) {
    const t = this.templates[name];
    const root = t.clone(true);
    root.position.set(0, 0, 0);
    const parts = {};
    const mats = [];
    root.traverse((o) => {
      if (o.isMesh && o.userData.isOutline) return;
      if (o.isMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
        let mm = o.material.clone();
        if (recolor && recolor[mm.name]) {
          mm.color.set(recolor[mm.name]);
          const e = mm.emissive;
          if (e && (e.r || e.g || e.b)) e.set(recolor[mm.name]).multiplyScalar(Math.max(0.6, Math.max(e.r, e.g, e.b)));
        }
        if (mm.name === 'Gel') mm = this.gelify(mm);
        toonify(mm, 'char');
        o.material = mm;
        o.material.emissive = o.material.emissive || new THREE.Color();
        o.material.userData.baseEmissive = o.material.emissive.clone();
        mats.push(o.material);
      }
      const key = o.name.replace(name + '_', '');
      parts[key] = o;
      o.userData.rest = { p: o.position.clone(), r: o.rotation.clone(), s: o.scale.clone() };
    });
    addOutlines(root);
    const outlineMats = [];
    root.traverse((o) => { if (o.userData.isOutline) { o.material = o.material.clone(); outlineMats.push(o.material); } });
    return { root, parts, mats, outlineMats };
  }
}
