import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Heightfield, buildTerrain } from './terrain.js';
import { createWater } from './water.js';
import { createGrass } from './grass.js';
import { Vegetation } from './vegetation.js';
import { ModelLibrary } from '../actors/models.js';
import { enhanceSurface } from './surfaces.js';
import { Ambience } from './ambience.js';

export const AREAS = {
  castle: { name: 'アルセリア城', x: -40, z: 60, test: (x, z) => Math.abs(x + 40) < 33 && Math.abs(z - 60) < 34, music: 'castle' },
  village: { name: 'ミナトの村', x: 140, z: 110, test: (x, z) => Math.hypot(x - 140, z - 110) < 40, music: 'town' },
  tower: { name: 'まおうの塔', x: 70, z: -215, test: (x, z) => Math.hypot(x - 70, z + 215) < 34, music: null },
};

/** 当たり判定（回転した箱と円）。空間ハッシュで近傍だけ調べる */
class Colliders {
  constructor() { this.cell = 16; this.map = new Map(); }
  key(i, j) { return i * 73856093 ^ j * 19349663; }
  add(c) {
    const r = c.r ?? Math.hypot(c.hw, c.hd);
    const i0 = Math.floor((c.x - r) / this.cell), i1 = Math.floor((c.x + r) / this.cell);
    const j0 = Math.floor((c.z - r) / this.cell), j1 = Math.floor((c.z + r) / this.cell);
    for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) {
      const k = this.key(i, j);
      if (!this.map.has(k)) this.map.set(k, []);
      this.map.get(k).push(c);
    }
  }
  near(x, z) { return this.map.get(this.key(Math.floor(x / this.cell), Math.floor(z / this.cell))) || []; }
  /** 半径 rad の円を押し出す。押し出したら true */
  resolve(p, rad) {
    let hit = false;
    for (const c of this.near(p.x, p.z)) {
      if (c.disabled) continue;
      if (c.r != null) {
        const dx = p.x - c.x, dz = p.z - c.z, d = Math.hypot(dx, dz), m = c.r + rad;
        if (d < m && d > 1e-5) { p.x = c.x + (dx / d) * m; p.z = c.z + (dz / d) * m; hit = true; }
        continue;
      }
      const cs = Math.cos(c.rot), sn = Math.sin(c.rot);
      const dx = p.x - c.x, dz = p.z - c.z;
      const lx = dx * cs - dz * sn, lz = dx * sn + dz * cs;
      const qx = Math.max(-c.hw, Math.min(c.hw, lx)), qz = Math.max(-c.hd, Math.min(c.hd, lz));
      let ex = lx - qx, ez = lz - qz;
      let d = Math.hypot(ex, ez);
      if (d >= rad) continue;
      let nlx, nlz;
      if (d < 1e-5) {
        // 中に入り込んだ：一番近い面へ
        const px = c.hw - Math.abs(lx), pz = c.hd - Math.abs(lz);
        if (px < pz) { nlx = Math.sign(lx) * (c.hw + rad); nlz = lz; } else { nlx = lx; nlz = Math.sign(lz) * (c.hd + rad); }
      } else {
        nlx = qx + (ex / d) * rad; nlz = qz + (ez / d) * rad;
      }
      p.x = c.x + nlx * cs + nlz * sn;
      p.z = c.z - nlx * sn + nlz * cs;
      hit = true;
    }
    return hit;
  }
}

export class World {
  constructor(scene, renderer, sky, q, camera) {
    this.scene = scene;
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
    const report = () => { const v = Object.values(prog); onProgress(v.reduce((a, b) => a + b, 0) / 4); };
    const get = (key, url) => new Promise((res, rej) => loader.load(url, (g) => { prog[key] = 1; report(); res(g); },
      (e) => { if (e.total) { prog[key] = e.loaded / e.total; report(); } }, rej));
    const json = fetch('assets/world.json').then((r) => r.json()).then((j) => { prog.json = 1; report(); return j; });
    const [wg, pg, cg, data] = await Promise.all([get('w', files.world), get('p', files.props), get('c', files.chars), json]);
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
    return this;
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
