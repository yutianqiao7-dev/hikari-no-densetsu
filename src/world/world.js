import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Heightfield, buildTerrain } from './terrain.js';
import { createWater } from './water.js';
import { createGrass } from './grass.js';
import { Vegetation } from './vegetation.js';
import { ModelLibrary } from '../actors/models.js';
import { enhanceSurface } from './surfaces.js';
import { Ambience } from './ambience.js';
import { Colliders } from './colliders.js';
import { Interiors } from './interiors.js';
import { encounterTable, islandEncounter } from '../game/data.js';

/** はじまりの島の町・城など（名前・BGM・範囲） */
export const AREAS = {
  castle: { name: 'アルセリア城', x: -40, z: 60, test: (x, z) => Math.abs(x + 40) < 33 && Math.abs(z - 60) < 34, music: 'castle' },
  village: { name: 'ミナトの村', x: 140, z: 110, test: (x, z) => Math.hypot(x - 140, z - 110) < 40, music: 'town' },
  tower: { name: 'まおうの塔', x: 70, z: -215, test: (x, z) => Math.hypot(x - 70, z + 215) < 34, music: null },
};

/**
 * 島。offset は海の上（竜で飛ぶとき）での位置。島の中ではそれぞれ自分の原点を中心にした座標で動く。
 * camp は町（キャンプ）の中心、dungeon はダンジョンの入口マーカー。
 */
export const ISLANDS = {
  main: { name: 'アルセリア島', offset: [0, 0], radius: 300, music: 'field' },
  desert: { name: '灼砂の島 サンドラ', offset: [1180, 260], radius: 230, music: 'desert', camp: 'オアシスの町 ルミナ' },
  ice: { name: '氷雪の島 フロスティア', offset: [-280, -1180], radius: 230, music: 'ice', camp: 'ゆきの村 シルフェ' },
  volcano: { name: '炎獄の島 ボルカニア', offset: [-1180, 380], radius: 230, music: 'volcano', camp: 'かじやの里 ゴルド' },
  dark: { name: '闇の島 ネクロス', offset: [320, 1260], radius: 230, music: 'dark', camp: 'レジスタンスの砦' },
};

export class World {
  constructor(scene, renderer, sky, q, camera, fx) {
    this.scene = scene;
    this.fx = fx;
    this.camera = camera;
    this.renderer = renderer;
    this.sky = sky;
    this.q = q;
    this.maps = {};
    this.map = null;
    this.sea = false;
    this.loader = new GLTFLoader();
    this.shared = {
      uTime: { value: 0 },
      uDay: { value: 1 },
      uWind: { value: new THREE.Vector2(0.8, 0.6) },
    };
  }

  /** Blender で同名マテリアルが重複すると「.001」などが付くので取り除く */
  static cleanNames(scene) {
    scene.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) m.name = m.name.replace(/\.\d+$/, '');
    });
  }

  gltf(url, onP) {
    return new Promise((res, rej) => this.loader.load(url, res, (e) => { if (e.total && onP) onP(e.loaded / e.total); }, rej));
  }

  async load(onProgress) {
    const prog = {};
    const report = () => { const v = Object.values(prog); onProgress(v.reduce((a, b) => a + b, 0) / 5); };
    const get = (key, url) => this.gltf(url, (p) => { prog[key] = p; report(); }).then((g) => { prog[key] = 1; report(); return g; });
    const json = fetch('assets/world.json').then((r) => r.json()).then((j) => { prog.json = 1; report(); return j; });
    const [wg, pg, cg, ig, data] = await Promise.all([get('w', 'assets/world.glb'), get('p', 'assets/props.glb'), get('c', 'assets/characters.glb'), get('i', 'assets/interiors.glb'), json]);
    for (const g of [wg, pg, cg, ig]) World.cleanNames(g.scene);
    this.propsScene = pg.scene;

    this.water = createWater({ uvParams: new THREE.Vector4() }, null, this.sky);
    this.scene.add(this.water);

    const main = this.makeMap('main', wg.scene, data);
    this.seal = wg.scene.getObjectByName('TowerSeal');
    this.lib = new ModelLibrary(cg);
    ig.scene.traverse((o) => { if (o.isMesh) enhanceSurface(o.material, main.terrain.heightTex, main.hf.uvParams, true); });
    this.interiors = new Interiors(data.interiors, ig, this.scene, this.fx);
    this.useMap('main');
    return this;
  }

  /** 島の描画物・高さ・当たり判定・マーカーをまとめた「マップ」を作る */
  makeMap(id, gscene, data) {
    const isl = ISLANDS[id];
    const hf = new Heightfield(data.terrain);
    gscene.updateMatrixWorld(true);
    let tMesh = null;
    gscene.traverse((o) => { if (!tMesh && /^Terrain/.test(o.name)) tMesh = o; });
    const tMeshReal = tMesh.isMesh ? tMesh : tMesh.children.find((c) => c.isMesh);
    const terrain = buildTerrain(hf, tMeshReal, this.shared);
    const offU = { value: new THREE.Vector2() };
    const uv = hf.uvParams;
    const map = { id, isl, hf, terrain, data, markers: data.markers, windows: [], glow: [], lava: [], offU, areas: id === 'main' ? AREAS : {} };

    // 建物（地形と海のダミーは捨てる）
    const remove = [];
    gscene.traverse((o) => {
      const dummy = (n) => /^Terrain/.test(n) || n === 'Water';
      if (dummy(o.name) || (o.parent && dummy(o.parent.name))) { remove.push(o); return; }
      if (o.isMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
        const m = o.material;
        if (/WindowLight/.test(m.name)) map.windows.push(m);
        if (/MagicGlow/.test(m.name)) map.glow.push(m);
        if (/^Lava/.test(m.name)) { map.lava.push(m); o.castShadow = false; }
        if (/WellWater/.test(m.name)) { m.roughness = 0.05; m.metalness = 0.2; }
        if (/Gold/.test(m.name)) m.envMapIntensity = 1.5;
        enhanceSurface(m, terrain.heightTex, uv, false, offU);
      }
    });
    for (const o of remove) o.parent && o.parent.remove(o);

    const root = new THREE.Group();
    root.name = 'Map_' + id;
    root.add(terrain.mesh);
    root.add(gscene);
    map.buildings = gscene;
    map.veg = new Vegetation(this.propsScene, data.scatter, hf, this.shared, this.q);
    root.add(map.veg.group);
    root.visible = false;
    this.scene.add(root);
    map.root = root;

    map.grass = createGrass(this.q, hf, terrain.heightTex, terrain.colorTex, this.shared);
    map.grass.visible = false;
    this.scene.add(map.grass);

    map.colliders = new Colliders();
    for (const c of data.colliders) map.colliders.add({ ...c });
    for (const c of map.veg.colliders) map.colliders.add(c);
    map.amb = new Ambience(this.scene, map, this.q);
    map.amb.setVisible(false);
    // 島の町・名所（Blender のマーカー Area_<名前>_<半径> から）
    for (const [k, m] of Object.entries(data.markers)) {
      const a = /^Area_([A-Za-z]+)_(\d+)$/.exec(k);
      if (!a) continue;
      const r = +a[2], info = (data.areas || {})[a[1]] || {};
      map.areas[a[1]] = { name: info.name || a[1], x: m.x, z: m.z, music: info.music ?? 'town', test: (x, z) => Math.hypot(x - m.x, z - m.z) < r };
    }
    map.env = this.makeFieldEnv(map);
    this.maps[id] = map;
    return map;
  }

  /** 島を読み込む（未読み込みのときだけ） */
  async ensureMap(id, onP) {
    if (this.maps[id]) return this.maps[id];
    const [g, data] = await Promise.all([this.gltf(`assets/island_${id}.glb`, onP), fetch(`assets/island_${id}.json`).then((r) => r.json())]);
    World.cleanNames(g.scene);
    const map = this.makeMap(id, g.scene, data);
    if (this.onMapLoaded) this.onMapLoaded(map);
    return map;
  }

  /** いまいる島を切り替える（島の中の座標系に戻す） */
  useMap(id) {
    const m = this.maps[id];
    for (const o of Object.values(this.maps)) { o.root.visible = false; o.grass.visible = false; o.amb.setVisible(false); }
    this.sea = false;
    this.map = m;
    m.root.visible = true;
    m.root.position.set(0, 0, 0);
    m.offU.value.set(0, 0);
    m.grass.visible = true;
    m.amb.setVisible(true);
    this.hf = m.hf;
    this.terrain = m.terrain;
    this.veg = m.veg;
    this.grass = m.grass;
    this.colliders = m.colliders;
    this.markers = m.markers;
    this.data = m.data;
    this.buildings = m.buildings;
    this.amb = m.amb;
    this.areas = m.areas;
    this.fieldEnv = m.env;
    this.water.position.set(0, 0, 0);
    this.water.setTerrain(m.terrain.heightTex, m.hf.uvParams);
    this.fieldGroups = [m.root, this.water, m.grass, this.sky.sky];
    this.amb.setViewport && this.amb.setViewport(this.viewportH || 800);
    return m;
  }

  /** 竜で飛んでいるあいだ：読み込んだ島をすべて海の上の位置に並べる */
  enterSea() {
    this.sea = true;
    for (const o of Object.values(this.maps)) {
      const [ox, oz] = o.isl.offset;
      o.root.visible = true;
      o.root.position.set(ox, 0, oz);
      o.offU.value.set(ox, oz);
      o.grass.visible = false;
      o.amb.setVisible(false);
    }
    this.water.setTerrain(null);
    this.fieldGroups = [...Object.values(this.maps).map((o) => o.root), this.water, this.sky.sky];
  }

  /** 海の上の位置 → どの島の上か（島のローカル座標つき） */
  islandAt(x, z) {
    for (const o of Object.values(this.maps)) {
      const [ox, oz] = o.isl.offset;
      const lx = x - ox, lz = z - oz;
      if (Math.abs(lx) < o.hf.half && Math.abs(lz) < o.hf.half) return { map: o, lx, lz, h: o.hf.height(lx, lz) };
    }
    return null;
  }

  /** フィールドの env（ダンジョンの Floor と同じインターフェース） */
  makeFieldEnv(map) {
    const hf = map.hf, id = map.id;
    const lim = hf.half - 20;
    const areaAt = (x, z) => { for (const [k, a] of Object.entries(map.areas)) if (a.test(x, z)) return k; return null; };
    return {
      kind: 'field', id: id === 'main' ? 'field' : id, island: id, name: map.isl.name,
      colliders: map.colliders,
      height: (x, z) => hf.height(x, z),
      walkable: (x, z, y) => {
        const h = hf.height(x, z);
        if (h < 0.2) return false;
        if (Math.abs(x) > lim || Math.abs(z) > lim) return false;
        if (h - y > 0.9 && hf.slope(x, z) > 0.95) return false;
        return true;
      },
      areaAt,
      trigger: () => null,
      encounter: (x, z, night) => (id === 'main' ? encounterTable(x, z, night, hf.height(x, z)) : islandEncounter(id, x, z, night, hf.height(x, z))),
      spawnPoint: (p) => {
        const a = Math.random() * Math.PI * 2, r = 34 + Math.random() * 30;
        const x = p.x + Math.cos(a) * r, z = p.z + Math.sin(a) * r;
        const h = hf.height(x, z);
        if (h > 1.3 && hf.slope(x, z) < 0.6 && !areaAt(x, z) && Math.abs(x) < lim && Math.abs(z) < lim) return { x, y: h, z };
        return null;
      },
      monsterOK: (x, z) => hf.height(x, z) > 1.0 && hf.slope(x, z) < 0.8 && !areaAt(x, z),
    };
  }

  /** フィールドの描画物をまとめて表示・非表示（ダンジョンに入ったとき） */
  setFieldVisible(v) {
    for (const g of this.fieldGroups) g.visible = v;
    this.amb.setVisible(v);
  }

  marker(name) {
    const m = this.markers[name];
    return m ? { pos: new THREE.Vector3(m.x, m.y, m.z), rot: m.rot } : null;
  }

  areaAt(x, z) { return this.fieldEnv.areaAt(x, z); }

  walkable(x, z, fromY) { return this.fieldEnv.walkable(x, z, fromY); }

  update(dt, t, camPos, player) {
    this.shared.uTime.value = t;
    this.shared.uDay.value = this.sky.day;
    if (this.interiors.current) {
      this.interiors.update(dt, t, player, camPos);
      return;
    }
    this.water.update(dt, this.sky);
    const night = this.sky.night;
    const glowI = 5 + Math.sin(t * 2.2) * 2;
    const lavaI = 2.6 + Math.sin(t * 1.3) * 0.5 + Math.sin(t * 3.7) * 0.25;
    if (this.sea) {
      // 海の上：水面をカメラに追従させ、各島の木を島ごとの座標で更新
      this.water.position.set(Math.round(camPos.x / 50) * 50, 0, Math.round(camPos.z / 50) * 50);
      const lc = new THREE.Vector3();
      for (const o of Object.values(this.maps)) {
        lc.set(camPos.x - o.isl.offset[0], camPos.y, camPos.z - o.isl.offset[1]);
        o.veg.update(lc, this.camera);
        for (const m of o.lava) m.emissiveIntensity = lavaI;
        for (const m of o.glow) m.emissiveIntensity = glowI;
      }
      return;
    }
    const m = this.map;
    this.grass.update(player, player);
    this.veg.update(camPos, this.camera);
    for (const w of m.windows) w.emissiveIntensity = 0.04 + night * 5.5 + this.sky.dusk * 1.5;
    for (const g of m.glow) g.emissiveIntensity = glowI;
    for (const l of m.lava) l.emissiveIntensity = lavaI;
    this.amb.update(dt, t, camPos, this.sky);
  }
}
