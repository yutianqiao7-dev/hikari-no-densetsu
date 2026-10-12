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
import { encounterTable } from '../game/data.js';

export const AREAS = {
  castle: { name: 'アルセリア城', x: -40, z: 60, test: (x, z) => Math.abs(x + 40) < 33 && Math.abs(z - 60) < 34, music: 'castle' },
  village: { name: 'ミナトの村', x: 140, z: 110, test: (x, z) => Math.hypot(x - 140, z - 110) < 40, music: 'town' },
  tower: { name: 'まおうの塔', x: 70, z: -215, test: (x, z) => Math.hypot(x - 70, z + 215) < 34, music: null },
};

export class World {
  constructor(scene, renderer, sky, q, camera, fx) {
    this.scene = scene;
    this.fx = fx;
    this.camera = camera;
    this.renderer = renderer;
    this.sky = sky;
    this.q = q;
    this.colliders = new Colliders();
    this.glow = [];
    this.windows = [];
  }

  async load(onProgress) {
    const manager = new THREE.LoadingManager();
    const loader = new GLTFLoader(manager);
    const files = { world: 'assets/world.glb', props: 'assets/props.glb', chars: 'assets/characters.glb' };
    const prog = {};
    const report = () => { const v = Object.values(prog); onProgress(v.reduce((a, b) => a + b, 0) / 5); };
    const get = (key, url) => new Promise((res, rej) => loader.load(url, (g) => { prog[key] = 1; report(); res(g); },
      (e) => { if (e.total) { prog[key] = e.loaded / e.total; report(); } }, rej));
    const json = fetch('assets/world.json').then((r) => r.json()).then((j) => { prog.json = 1; report(); return j; });
    const [wg, pg, cg, ig, data] = await Promise.all([get('w', files.world), get('p', files.props), get('c', files.chars), get('i', 'assets/interiors.glb'), json]);
    // Blender で同名マテリアルが重複すると「.001」などが付くので取り除く
    for (const g of [wg, pg, cg, ig]) g.scene.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) m.name = m.name.replace(/\.\d+$/, '');
    });
    this.data = data;
    this.markers = data.markers;

    // 地形
    const hf = new Heightfield(data.terrain);
    this.hf = hf;
    wg.scene.updateMatrixWorld(true);
    const tMesh = wg.scene.getObjectByName('Terrain');
    const tMeshReal = tMesh.isMesh ? tMesh : tMesh.children.find((c) => c.isMesh);
    const terrain = buildTerrain(hf, tMeshReal);
    this.terrain = terrain;
    this.shared = terrain.shared;
    this.scene.add(terrain.mesh);

    // 建物
    const remove = [];
    wg.scene.traverse((o) => {
      if (o.name === 'Terrain' || o.name === 'Water' || (o.parent && (o.parent.name === 'Terrain' || o.parent.name === 'Water'))) { remove.push(o); return; }
      if (o.isMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
        const m = o.material;
        if (/WindowLight/.test(m.name)) this.windows.push(m);
        if (/MagicGlow/.test(m.name)) this.glow.push(m);
        if (/WellWater/.test(m.name)) { m.roughness = 0.05; m.metalness = 0.2; }
        if (/Gold/.test(m.name)) m.envMapIntensity = 1.5;
        enhanceSurface(m, terrain.heightTex, hf.uvParams);
      }
    });
    for (const o of remove) o.parent && o.parent.remove(o);
    this.buildings = wg.scene;
    this.scene.add(wg.scene);

    // 海・草・木
    this.water = createWater(hf, terrain.heightTex, this.sky);
    this.scene.add(this.water);
    this.grass = createGrass(this.q, hf, terrain.heightTex, terrain.colorTex, terrain.shared);
    this.scene.add(this.grass);
    this.veg = new Vegetation(pg.scene, data.scatter, hf, terrain.shared, this.q);
    this.scene.add(this.veg.group);

    for (const c of data.colliders) this.colliders.add({ ...c });
    for (const c of this.veg.colliders) this.colliders.add(c);

    this.lib = new ModelLibrary(cg);
    this.amb = new Ambience(this.scene, this, this.q);
    ig.scene.traverse((o) => { if (o.isMesh) enhanceSurface(o.material, terrain.heightTex, hf.uvParams, true); });
    this.interiors = new Interiors(data.interiors, ig, this.scene, this.fx);
    this.seal = wg.scene.getObjectByName('TowerSeal');
    this.fieldEnv = this.makeFieldEnv();
    this.fieldGroups = [terrain.mesh, this.water, this.grass, this.veg.group, wg.scene, this.sky.sky];
    return this;
  }

  /** フィールドの env（ダンジョンの Floor と同じインターフェース） */
  makeFieldEnv() {
    const w = this, hf = this.hf;
    return {
      kind: 'field', id: 'field', name: 'フィールド',
      colliders: this.colliders,
      height: (x, z) => hf.height(x, z),
      walkable: (x, z, y) => w.walkable(x, z, y),
      areaAt: (x, z) => w.areaAt(x, z),
      trigger: () => null,
      encounter: (x, z, night) => encounterTable(x, z, night),
      spawnPoint: (p) => {
        const a = Math.random() * Math.PI * 2, r = 34 + Math.random() * 30;
        const x = p.x + Math.cos(a) * r, z = p.z + Math.sin(a) * r;
        const h = hf.height(x, z);
        if (h > 1.3 && hf.slope(x, z) < 0.6 && !w.areaAt(x, z) && Math.abs(x) < 290 && Math.abs(z) < 290) return { x, y: h, z };
        return null;
      },
      monsterOK: (x, z) => hf.height(x, z) > 1.0 && hf.slope(x, z) < 0.8 && !w.areaAt(x, z),
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

  areaAt(x, z) {
    for (const [k, a] of Object.entries(AREAS)) if (a.test(x, z)) return k;
    return null;
  }

  /** 歩けるか（海・急斜面は不可） */
  walkable(x, z, fromY) {
    const h = this.hf.height(x, z);
    if (h < 0.2) return false;
    if (Math.abs(x) > 300 || Math.abs(z) > 300) return false;
    if (h - fromY > 0.9 && this.hf.slope(x, z) > 0.95) return false;
    return true;
  }

  update(dt, t, camPos, player) {
    if (this.interiors.current) {
      this.shared.uTime.value = t;
      this.interiors.update(dt, t, player, camPos);
      return;
    }
    this.shared.uTime.value = t;
    this.shared.uDay.value = this.sky.day;
    this.water.update(dt, this.sky);
    this.grass.update(player, player);
    this.veg.update(camPos, this.camera);
    const night = this.sky.night;
    for (const m of this.windows) m.emissiveIntensity = 0.3 + night * 5.5 + this.sky.dusk * 1.5;
    for (const m of this.glow) m.emissiveIntensity = 5 + Math.sin(t * 2.2) * 2;
    this.amb.update(dt, t, camPos, this.sky);
  }
}
