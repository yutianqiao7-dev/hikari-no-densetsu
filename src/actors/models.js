import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

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
        if (recolor && recolor[mm.name]) mm.color.set(recolor[mm.name]);
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
