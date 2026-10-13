import * as THREE from 'three';
import { Colliders } from './colliders.js';

const WALK_BLOCK = new Set(['#', 'W', 'P', 'T', 'b', 't', 'c', 'h', 'k', 'f', 'y', 'n', 'p']);
const FURNITURE = 'bthkfn';

/**
 * ダンジョン・塔の 1 フロア。フィールドと同じインターフェース（env）を持つ。
 *   height / walkable / colliders / trigger / spawnPoint / monsterOK / encounter
 */
class Floor {
  constructor(info, group, owner) {
    this.kind = 'interior';
    this.id = info.id;
    this.name = info.name;
    this.style = info.kind;           // 'cave' | 'tower' | 'room' | 'castle'
    this.indoor = info.kind === 'room' || info.kind === 'castle';
    this.door = info.door;
    this.exit = info.exit;
    this.pots = (info.pots || []).map((p) => ({ ...p, pos: new THREE.Vector3(p.x, 0, p.z) }));
    this.info = info;
    this.group = group;
    this.owner = owner;
    this.grid = info.grid;
    this.W = this.grid[0].length;
    this.H = this.grid.length;
    this.ox = info.origin[0];
    this.oz = info.origin[1];
    this.cell = info.cell;
    this.colliders = new Colliders();
    this.spots = info.spots;
    this.chests = info.chests.map((c) => {
      const obj = group.getObjectByName(`INT_${info.id}_Chest${c.id.split('-')[1]}`);
      const lid = obj && obj.getObjectByName(`INT_${info.id}_Chest${c.id.split('-')[1]}_Lid`);
      return { ...c, obj, lid, pos: new THREE.Vector3(c.x, 0, c.z) };
    });
    this.orb = group.getObjectByName(`INT_${info.id}_Orb`);
    this.torches = info.torches.map(([x, y, z]) => new THREE.Vector3(x, y, z));
    this.glows = info.lights.map(([x, y, z, c]) => ({ p: new THREE.Vector3(x, y, z), c }));
    // 壁・柱・かがり火・宝箱の当たり判定
    const half = this.cell / 2;
    for (let j = 0; j < this.H; j++) for (let i = 0; i < this.W; i++) {
      const c = this.grid[j][i];
      const [x, z] = this.center(i, j);
      if (c === '#') this.colliders.add({ x, z, hw: half, hd: half, rot: 0 });
      else if (c === 'P') this.colliders.add({ x, z, r: 0.95 });
      else if (c === 'T') this.colliders.add({ x, z, r: 0.7 });
      else if (FURNITURE.includes(c)) this.colliders.add({ x, z, hw: half - 0.08, hd: half - 0.08, rot: 0 });
      else if (c === 'y') this.colliders.add({ x, z, r: 0.45 });
      else if (c === 'p') this.colliders.add({ x, z, r: 0.62 });
    }
    for (const c of this.chests) this.colliders.add({ x: c.x, z: c.z, hw: 0.55, hd: 0.4, rot: c.rot });
    this.lastCell = null;
  }

  center(i, j) { return [this.ox + (i + 0.5) * this.cell, this.oz + (j + 0.5) * this.cell]; }
  cellOf(x, z) { return [Math.floor((x - this.ox) / this.cell), Math.floor((z - this.oz) / this.cell)]; }
  at(i, j) { return (i >= 0 && j >= 0 && i < this.W && j < this.H) ? this.grid[j][i] : '#'; }
  charAt(x, z) { const [i, j] = this.cellOf(x, z); return this.at(i, j); }

  height() { return 0; }
  walkable(x, z) { return !WALK_BLOCK.has(this.charAt(x, z)); }
  areaAt() { return null; }

  /** 出口・階段に「入った瞬間」だけ反応する */
  trigger(x, z) {
    const [i, j] = this.cellOf(x, z);
    const key = i + ',' + j;
    const c = this.at(i, j);
    const fired = key !== this.lastCell && 'SUD'.includes(c) ? c : null;
    this.lastCell = key;
    return fired;
  }

  /** 到着位置：指定した種類のマスの隣の床 */
  arrival(kind) {
    const s = this.spots[kind] && this.spots[kind][0];
    if (!s) return null;
    const [i, j] = this.cellOf(s[0], s[1]);
    // 外周から離れる向きを優先（入ってきた扉を背にする）
    const dirs = j > this.H / 2 ? [[0, -1], [1, 0], [-1, 0], [0, 1]] : [[0, 1], [1, 0], [-1, 0], [0, -1]];
    for (const [di, dj] of dirs) {
      const c = this.at(i + di, j + dj);
      if (c === '.' || c === 'R' || c === 'r') {
        const [x, z] = this.center(i + di, j + dj);
        this.lastCell = `${i + di},${j + dj}`;
        return { pos: new THREE.Vector3(x, 0, z), rot: Math.atan2(di, dj) };
      }
    }
    return null;
  }

  encounter() {
    const T = {
      cave: { lv: 4, list: ['bat', 'bat_dark', 'mushroom_poison', 'golem', 'ghost', 'purun_red', 'skeleton', 'snake_cobra', 'wisp'] },
      tower: { lv: 6, list: ['ghost_blue', 'golem', 'bat_dark', 'ghost', 'skeleton_dark', 'gargoyle', 'wisp_blue', 'skeleton_dark', 'gargoyle'] },
      pyramid: { lv: 23, list: ['mummy', 'mummy', 'scorpion', 'sandsnake', 'mummy', 'wisp'] },
      icecave: { lv: 29, list: ['icewraith', 'penguin', 'icewolf', 'snowman', 'icewraith'] },
      lava: { lv: 35, list: ['salamander', 'magmagolem', 'flamewisp', 'firebird', 'lavapurun'] },
      darkcastle: { lv: 42, list: ['darkknight', 'skeleton_king', 'shadow', 'gargoyle_dark', 'evileye', 'darkknight'] },
    };
    return T[this.style] || T.tower;
  }

  /** モンスターの出現位置（プレイヤーから離れた床） */
  spawnPoint(p) {
    if (this.indoor) return null;
    for (let k = 0; k < 8; k++) {
      const i = Math.floor(Math.random() * this.W), j = Math.floor(Math.random() * this.H);
      if (this.at(i, j) !== '.' && this.at(i, j) !== 'R') continue;
      const [x, z] = this.center(i, j);
      const d = Math.hypot(x - p.x, z - p.z);
      if (d < 14 || d > 44) continue;
      return { x, y: 0, z };
    }
    return null;
  }
  monsterOK(x, z) { const c = this.charAt(x, z); return c === '.' || c === 'R' || c === 'C'; }
}

export class Interiors {
  constructor(data, gltf, scene, fx) {
    this.scene = scene;
    this.fx = fx;
    this.floors = {};
    for (const info of data.floors) {
      const g = gltf.scene.getObjectByName('INT_' + info.id);
      g.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = true; } });
      g.visible = false;
      scene.add(g);
      this.floors[info.id] = new Floor(info, g, this);
    }
    this.current = null;
    // かがり火の光（近い順に割り当て）と勇者のランタン
    this.lights = [];
    for (let i = 0; i < 6; i++) {
      const l = new THREE.PointLight(0xff9a40, 0, 18, 1.6);
      l.visible = false;
      scene.add(l);
      this.lights.push(l);
    }
    this.lantern = new THREE.PointLight(0xffd29a, 0, 24, 1.3);
    this.lantern.visible = false;
    scene.add(this.lantern);
    this.emitT = 0;
  }

  enter(id) {
    if (this.current) this.current.group.visible = false;
    this.current = this.floors[id];
    this.current.group.visible = true;
    for (const l of this.lights) l.visible = true;
    this.lantern.visible = true;
    this.assignT = 0;
    return this.current;
  }

  leave() {
    if (this.current) this.current.group.visible = false;
    this.current = null;
    for (const l of this.lights) { l.visible = false; l.intensity = 0; }
    this.lantern.visible = false;
  }

  update(dt, t, heroPos, cam) {
    const f = this.current;
    if (!f) return;
    // ランタン
    this.lantern.position.set(heroPos.x, heroPos.y + 2.4, heroPos.z);
    this.lantern.intensity = f.indoor ? 0 : ({ cave: 18, icecave: 12, lava: 10, pyramid: 14, darkcastle: 15 }[f.style] || 13) + Math.sin(t * 7) * 0.6;
    // 光源（かがり火・水晶・出口の光）を近い順に
    this.assignT -= dt;
    if (this.assignT <= 0) {
      this.assignT = 0.4;
      const src = [...f.torches.map((p) => ({ p, c: 0xff9a40, torch: true })), ...f.glows];
      src.sort((a, b) => a.p.distanceToSquared(cam) - b.p.distanceToSquared(cam));
      this.lights.forEach((l, i) => {
        const s = src[i];
        if (s) { l.position.copy(s.p); l.color.set(s.c); l.userData.torch = !!s.torch; l.visible = true; } else l.visible = false;
      });
    }
    this.lights.forEach((l, i) => {
      const base = f.indoor ? (l.userData.torch ? 10 : 9) : (l.userData.torch ? 22 : 14);
      l.intensity = l.userData.torch ? base + Math.sin(t * 13 + i * 5) * 2 + Math.sin(t * 7.3 + i) * 1.5 : base;
    });
    // 炎のパーティクル
    this.emitT -= dt;
    if (this.emitT <= 0) {
      this.emitT = 0.05;
      for (const p of f.torches) {
        if (p.distanceToSquared(heroPos) > 45 * 45) continue;
        const small = f.indoor;
        this.fx.emit({ pos: p.clone().add(new THREE.Vector3(0, 0.05, 0)), count: small ? 1 : 2, color: [0xffcc55, 0xff7722, 0xff4411], speed: 0.25, up: small ? 0.9 : 1.6, life: small ? 0.4 : 0.55, size: small ? 0.22 : 0.45, grow: -0.6, drag: 1.5, spread: small ? 0.15 : 0.35, flat: true });
        if (Math.random() < 0.1) this.fx.emit({ pos: p.clone().add(new THREE.Vector3(0, 0.6, 0)), count: 1, color: 0xffaa44, speed: 0.4, up: 2.4, life: 1.4, size: 0.08, drag: 0.5 });
      }
    }
    if (f.orb && f.orb.visible) {
      f.orb.rotation.y += dt;
      f.orb.position.y = 1.55 + Math.sin(t * 2) * 0.08;
    }
  }
}
