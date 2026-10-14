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
        p.roughness = 0.52;
        p.sheen = 0.35;
        p.sheenRoughness = 0.6;
        p.sheenColor = new THREE.Color(1.0, 0.55, 0.45);
      }
      if (m.side === THREE.DoubleSide) p.side = THREE.DoubleSide;
      r = p;
    }
    if (/Blade|Silver|Armor|Gold|Sapphire|Ruby/i.test(n)) r.envMapIntensity = 1.6;
    const dk = detailKind(n);
    if (dk && !/^Mon_/.test(n)) addDetail(r, dk);
    if (/Eye|Iris|Pupil/i.test(n)) { r.roughness = 0.08; r.envMapIntensity = 1.4; }
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
    root.traverse((o) => {
      if (o.isMesh) o.frustumCulled = false;
      if (o !== root && o.name.startsWith(name + '_')) {
        const key = o.name.slice(name.length + 1);
        if (!parts[key]) parts[key] = o;
      }
    });
    return { root, mixer, actions, parts };
  }

  /** モンスター（部位ごとのオブジェクト） */
  monster(name, recolor) {
    const t = this.templates[name];
    const root = t.clone(true);
    root.position.set(0, 0, 0);
    const parts = {};
    const mats = [];
    root.traverse((o) => {
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
        o.material = mm;
        o.material.emissive = o.material.emissive || new THREE.Color();
        o.material.userData.baseEmissive = o.material.emissive.clone();
        mats.push(o.material);
      }
      const key = o.name.replace(name + '_', '');
      parts[key] = o;
      o.userData.rest = { p: o.position.clone(), r: o.rotation.clone(), s: o.scale.clone() };
    });
    return { root, parts, mats };
  }
}
