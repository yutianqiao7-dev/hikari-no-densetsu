import * as THREE from 'three';
import { Humanoid, Monster, angDiff } from '../actors/actor.js';
import { MONSTERS, encounterTable } from './data.js';
import { AREAS } from '../world/world.js';

const NPC_MODELS = {
  King: 'King', Guard1: 'Guard', Guard2: 'Guard', Guard3: 'Guard', Guard4: 'Guard', Minister: 'Minister',
  Innkeeper: 'Innkeeper', Merchant: 'Merchant', Elder: 'Elder', Girl: 'Girl', Villager1: 'Villager', Villager2: 'Villager',
};
const WANDER = new Set(['Girl', 'Villager1', 'Villager2', 'Minister']);

export class Field {
  constructor(game) {
    this.g = game;
    const { world, scene } = game;
    this.world = world;
    this.scene = scene;
    this.camera = game.camera;

    // 勇者
    this.hero = new Humanoid(world.lib, 'Hero');
    scene.add(this.hero.root);
    this.pos = new THREE.Vector3();
    this.vel = new THREE.Vector3();
    this.facing = 0;

    // カメラ
    this.cam = { yaw: 0, pitch: 0.32, dist: 8.5, target: new THREE.Vector3(), lastManual: 0 };
    this.camPos = new THREE.Vector3();

    // NPC
    this.npcs = [];
    for (const [mk, model] of Object.entries(NPC_MODELS)) {
      const m = world.marker(mk);
      if (!m || !world.lib.has(model)) continue;
      const h = new Humanoid(world.lib, model);
      h.root.position.copy(m.pos);
      h.root.rotation.y = m.rot;
      scene.add(h.root);
      this.npcs.push({ id: mk, h, home: m.pos.clone(), pos: m.pos.clone(), rot: m.rot, baseRot: m.rot, wander: WANDER.has(mk), target: null, wait: Math.random() * 4, talking: false });
    }
    this.signs = ['Sign1', 'Sign2', 'Sign3'].map((id) => ({ id, pos: world.marker(id).pos }));

    // ボス
    const bm = world.marker('Boss');
    this.boss = new Monster(world.lib, MONSTERS.dragon);
    this.boss.root.position.copy(bm.pos).add(new THREE.Vector3(0, 0, 7));
    this.boss.root.position.y = world.hf.height(this.boss.root.position.x, this.boss.root.position.z);
    this.boss.root.rotation.y = bm.rot;
    this.bossMarker = { pos: this.boss.root.position.clone(), rot: bm.rot };
    scene.add(this.boss.root);

    // シンボルエンカウントのモンスター
    this.mons = [];
    this.spawnT = 0;
    this.safeT = 0;
    this.stepT = 0;
    this.area = null;
    this.hint = document.createElement('div');
    this.hint.className = 'talk-hint hidden';
    game.ui.root.appendChild(this.hint);
  }

  place(pos, rot) {
    this.pos.copy(pos);
    this.pos.y = this.world.hf.height(pos.x, pos.z);
    this.facing = rot;
    this.cam.yaw = rot + Math.PI;
    this.hero.root.position.copy(this.pos);
    this.hero.root.rotation.y = rot;
    this.snapCamera();
  }

  snapCamera() {
    this.cam.target.copy(this.pos).add(new THREE.Vector3(0, 1.35, 0));
    this.updateCamera(1, true);
  }

  setVisible(v) {
    this.visibleAll = v;
    for (const n of this.npcs) n.h.root.visible = v;
    for (const m of this.mons) m.root.visible = v;
    this.boss.root.visible = v && !this.g.state.flags.cleared;
    if (!v) this.hint.classList.add('hidden');
  }

  // ------------------------------------------------------------ 毎フレーム
  update(dt, t, mv, inputCam) {
    const w = this.world;
    // カメラ入力
    if (inputCam.yaw || inputCam.pitch) this.cam.lastManual = t;
    this.cam.yaw += inputCam.yaw;
    this.cam.pitch = THREE.MathUtils.clamp(this.cam.pitch + inputCam.pitch, -0.05, 1.2);
    this.cam.dist = THREE.MathUtils.clamp(this.cam.dist + inputCam.zoom, 3.2, 18);
    inputCam.yaw = inputCam.pitch = inputCam.zoom = 0;

    // 移動
    const yaw = this.cam.yaw;
    const fx = -Math.sin(yaw), fz = -Math.cos(yaw);
    const rx = Math.cos(yaw), rz = -Math.sin(yaw);
    let dx = fx * -mv.y + rx * mv.x, dz = fz * -mv.y + rz * mv.x;
    const len = mv.len;
    let speed = 0;
    if (len > 0.05) {
      speed = len < 0.6 ? THREE.MathUtils.mapLinear(len, 0.05, 0.6, 0.8, 2.2) : THREE.MathUtils.mapLinear(len, 0.6, 1, 4.2, 7.2);
      const d = Math.hypot(dx, dz);
      dx /= d; dz /= d;
      const target = Math.atan2(dx, dz);
      this.facing += angDiff(this.facing, target) * Math.min(1, dt * 12);
    }
    const want = new THREE.Vector3(dx * speed, 0, dz * speed);
    this.vel.lerp(want, Math.min(1, dt * (speed > 0 ? 10 : 14)));
    const next = this.pos.clone().addScaledVector(this.vel, dt);
    if (w.walkable(next.x, next.z, this.pos.y)) {
      w.colliders.resolve(next, 0.42);
      for (const n of this.npcs) this.pushOut(next, n.pos, 0.85);
      if (!this.g.state.flags.cleared) this.pushOut(next, this.boss.root.position, 3.2);
      if (w.walkable(next.x, next.z, this.pos.y)) { this.pos.x = next.x; this.pos.z = next.z; }
    } else {
      // 斜面・水際ではすべるように
      const tx = this.pos.clone(); tx.x = next.x;
      const tz = this.pos.clone(); tz.z = next.z;
      if (w.walkable(tx.x, tx.z, this.pos.y)) this.pos.x = tx.x;
      else if (w.walkable(tz.x, tz.z, this.pos.y)) this.pos.z = tz.z;
      this.vel.multiplyScalar(0.5);
    }
    const gy = w.hf.height(this.pos.x, this.pos.z);
    this.pos.y += (gy - this.pos.y) * Math.min(1, dt * 18);
    this.hero.root.position.copy(this.pos);
    this.hero.root.rotation.y = this.facing;
    this.hero.speed = this.vel.length();
    this.hero.update(dt);

    // 足音・砂ぼこり
    if (this.hero.speed > 1) {
      this.stepT -= dt * this.hero.speed;
      if (this.stepT <= 0) {
        this.stepT = this.hero.speed > 3.6 ? 1.35 : 0.75;
        this.g.audio.sfx('step');
        if (this.hero.speed > 3.6) this.g.fx.emit({ pos: this.pos.clone().add(new THREE.Vector3(0, 0.1, 0)), count: 3, color: 0xb8a888, speed: 0.6, up: 0.4, life: 0.7, size: 0.35, grow: 1.5, drag: 2 });
      }
    }

    // カメラの自動追従（操作していないときは背中側へゆっくり回る）
    if (this.hero.speed > 2 && t - this.cam.lastManual > 1.6) {
      this.cam.yaw += angDiff(this.cam.yaw, this.facing + Math.PI) * Math.min(1, dt * 0.9);
    }
    this.updateCamera(dt);

    // NPC
    for (const n of this.npcs) this.updateNpc(n, dt);
    this.boss.root.visible = !this.g.state.flags.cleared;
    if (this.boss.root.visible) this.boss.update(dt);

    // エリア
    const area = w.areaAt(this.pos.x, this.pos.z);
    if (area !== this.area) {
      this.area = area;
      if (area) this.g.ui.showBanner(AREAS[area].name);
      this.g.updateMusic();
    }

    this.updateMonsters(dt, t);
    this.updateHint();
  }

  pushOut(p, c, r) {
    const dx = p.x - c.x, dz = p.z - c.z, d = Math.hypot(dx, dz);
    if (d < r && d > 1e-4) { p.x = c.x + (dx / d) * r; p.z = c.z + (dz / d) * r; }
  }

  updateCamera(dt, snap = false) {
    const c = this.cam;
    const tgt = this.pos.clone().add(new THREE.Vector3(0, 1.35, 0));
    c.target.lerp(tgt, snap ? 1 : Math.min(1, dt * 8));
    const cp = Math.cos(c.pitch), sp = Math.sin(c.pitch);
    const want = c.target.clone().add(new THREE.Vector3(Math.sin(c.yaw) * cp * c.dist, sp * c.dist + 0.4, Math.cos(c.yaw) * cp * c.dist));
    // 木の葉の中にカメラが入らないよう、目標からカメラへ向かって樹冠に当たったら手前に寄せる
    const dirv = want.clone().sub(c.target);
    const full = dirv.length();
    dirv.divideScalar(full);
    let lim = full;
    for (let k = 1; k <= 12; k++) {
      const d = (k / 12) * full;
      const q = c.target.clone().addScaledVector(dirv, d);
      for (const t of this.world.colliders.near(q.x, q.z)) {
        if (!t.tree) continue;
        const cy = t.y + 4.2 * t.tree, cr = 2.6 * t.tree;
        const dx = q.x - t.x, dz = q.z - t.z, dy = (q.y - cy) * 1.3;
        if (dx * dx + dz * dz + dy * dy < cr * cr) { lim = Math.min(lim, Math.max(2.2, d - 0.8)); break; }
      }
      if (lim < full) break;
    }
    if (lim < full) want.copy(c.target).addScaledVector(dirv, lim);
    const gh = this.world.hf.height(want.x, want.z) + 0.6;
    if (want.y < gh) want.y = gh;
    this.camPos.lerp(want, snap ? 1 : Math.min(1, dt * 10));
    this.camera.position.copy(this.camPos);
    this.camera.lookAt(c.target);
  }

  updateNpc(n, dt) {
    const h = n.h;
    let speed = 0;
    if (n.talking) {
      const want = Math.atan2(this.pos.x - n.pos.x, this.pos.z - n.pos.z);
      n.rot += angDiff(n.rot, want) * Math.min(1, dt * 8);
    } else if (n.wander) {
      if (n.target) {
        const d = new THREE.Vector3().subVectors(n.target, n.pos);
        d.y = 0;
        const dist = d.length();
        if (dist < 0.3) { n.target = null; n.wait = 2 + Math.random() * 5; }
        else {
          speed = 1.25;
          d.normalize();
          n.rot += angDiff(n.rot, Math.atan2(d.x, d.z)) * Math.min(1, dt * 5);
          const nx = n.pos.clone().addScaledVector(d, speed * dt);
          if (this.world.colliders.resolve(nx, 0.4)) n.target = null;
          if (nx.distanceTo(this.pos) > 1.0) n.pos.copy(nx);
          n.pos.y = this.world.hf.height(n.pos.x, n.pos.z);
        }
      } else {
        n.wait -= dt;
        if (n.wait <= 0) {
          const a = Math.random() * Math.PI * 2, r = 1 + Math.random() * 4;
          n.target = n.home.clone().add(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
        }
      }
    } else {
      n.rot += angDiff(n.rot, n.baseRot) * Math.min(1, dt * 3);
    }
    h.root.position.copy(n.pos);
    h.root.rotation.y = n.rot;
    h.speed = speed;
    // 遠くの NPC は描かない・動かさない（スマホ向けの軽量化）
    const d2 = n.pos.distanceToSquared(this.camera.position);
    h.root.visible = this.visibleAll !== false && d2 < 95 * 95;
    if (d2 < 70 * 70) h.update(dt);
  }

  /** 前方の話しかけられる相手 */
  findInteract() {
    let best = null, bd = 3.0;
    const fwd = new THREE.Vector3(Math.sin(this.facing), 0, Math.cos(this.facing));
    const check = (id, p, range = 3.0, kind = 'npc', obj = null) => {
      const d = new THREE.Vector3().subVectors(p, this.pos);
      d.y = 0;
      const dist = d.length();
      if (dist > range) return;
      if (dist > 0.6 && d.normalize().dot(fwd) < 0.2) return;
      if (dist < bd) { bd = dist; best = { id, kind, obj, pos: p }; }
    };
    for (const n of this.npcs) check(n.id, n.pos, 3.0, 'npc', n);
    for (const s of this.signs) check(s.id, s.pos, 2.4, 'sign');
    if (!this.g.state.flags.cleared) check('Boss', this.bossMarker.pos, 9, 'boss');
    return best;
  }

  updateHint() {
    const it = this.g.ui.busy ? null : this.findInteract();
    if (!it) { this.hint.classList.add('hidden'); return; }
    const p = it.pos.clone().add(new THREE.Vector3(0, it.kind === 'sign' ? 2.4 : it.kind === 'boss' ? 6 : 2.2, 0)).project(this.camera);
    if (p.z > 1) { this.hint.classList.add('hidden'); return; }
    this.hint.classList.remove('hidden');
    this.hint.textContent = it.kind === 'sign' ? 'しらべる' : it.kind === 'boss' ? 'たちむかう' : 'はなす';
    this.hint.style.left = ((p.x + 1) / 2) * window.innerWidth + 'px';
    this.hint.style.top = ((1 - p.y) / 2) * window.innerHeight + 'px';
  }

  // ------------------------------------------------------------ モンスター
  updateMonsters(dt, t) {
    const w = this.world;
    const night = this.g.sky.night > 0.5;
    this.safeT = Math.max(0, this.safeT - dt);
    const inSafe = !!this.area && this.area !== 'tower';
    this.spawnT -= dt;
    if (this.spawnT <= 0 && this.mons.length < 7) {
      this.spawnT = 1.2;
      const a = Math.random() * Math.PI * 2, r = 34 + Math.random() * 30;
      const x = this.pos.x + Math.cos(a) * r, z = this.pos.z + Math.sin(a) * r;
      const h = w.hf.height(x, z);
      if (h > 1.3 && w.hf.slope(x, z) < 0.6 && !w.areaAt(x, z) && Math.abs(x) < 290 && Math.abs(z) < 290) {
        const tab = encounterTable(x, z, night);
        const key = tab.list[Math.floor(Math.random() * tab.list.length)];
        const m = new Monster(w.lib, MONSTERS[key]);
        m.key = key;
        m.lv = tab.lv;
        m.root.position.set(x, h, z);
        m.home = m.root.position.clone();
        m.heading = Math.random() * Math.PI * 2;
        m.state = 'wander';
        m.wait = Math.random() * 2;
        m.setOpacity(0);
        m.fadeIn = 0;
        this.scene.add(m.root);
        this.mons.push(m);
      }
    }
    for (let i = this.mons.length - 1; i >= 0; i--) {
      const m = this.mons[i];
      const p = m.root.position;
      const toP = new THREE.Vector3().subVectors(this.pos, p);
      toP.y = 0;
      const dist = toP.length();
      if (dist > 95 || (m.leaving && m.opacity <= 0.01)) { this.removeMon(i); continue; }
      if (m.fadeIn < 1 && !m.leaving) { m.fadeIn = Math.min(1, m.fadeIn + dt * 1.5); m.setOpacity(m.fadeIn); }
      if (m.leaving) m.setOpacity(Math.max(0, m.opacity - dt * 1.5));
      let sp = 0;
      const fast = m.kind === 'Bat' ? 5.2 : m.kind === 'Golem' ? 2.6 : m.kind === 'Ghost' ? 3.8 : 4.0;
      if (!inSafe && this.safeT <= 0 && dist < 15 && !m.leaving) {
        m.state = 'chase';
        sp = fast;
        m.heading += angDiff(m.heading, Math.atan2(toP.x, toP.z)) * Math.min(1, dt * 6);
        if (dist < 1.25 + (m.def.scale || 1) * 0.4) { this.g.startBattle(m); return; }
      } else {
        if (m.state === 'chase') { m.state = 'wander'; m.wait = 1; }
        m.wait -= dt;
        if (m.wait < 0) {
          sp = 1.3;
          if (Math.random() < dt * 0.6) m.heading += (Math.random() - 0.5) * 2;
          if (m.wait < -3) m.wait = 1 + Math.random() * 3;
        }
        if (inSafe || this.safeT > 0) { m.heading += angDiff(m.heading, Math.atan2(-toP.x, -toP.z)) * Math.min(1, dt * 3); sp = Math.max(sp, 1.5); }
      }
      if (sp > 0) {
        const nx = p.x + Math.sin(m.heading) * sp * dt, nz = p.z + Math.cos(m.heading) * sp * dt;
        const h = w.hf.height(nx, nz);
        if (h > 1.0 && w.hf.slope(nx, nz) < 0.8 && !w.areaAt(nx, nz)) {
          const np = new THREE.Vector3(nx, h, nz);
          w.colliders.resolve(np, 0.5);
          p.x = np.x; p.z = np.z;
        } else m.heading += Math.PI * 0.7;
      }
      p.y += (w.hf.height(p.x, p.z) - p.y) * Math.min(1, dt * 10);
      m.root.rotation.y += angDiff(m.root.rotation.y, m.heading) * Math.min(1, dt * 8);
      m.speed = sp;
      if (dist < 70) m.update(dt);
    }
  }

  removeMon(i) {
    const m = this.mons[i];
    this.scene.remove(m.root);
    this.mons.splice(i, 1);
  }

  removeMonster(m) {
    const i = this.mons.indexOf(m);
    if (i >= 0) this.removeMon(i);
  }

  /** 戦闘から逃げたあと：しばらく襲われず、近くの魔物は離れていく */
  afterFlee() {
    this.safeT = 4;
    for (const m of this.mons) if (m.root.position.distanceTo(this.pos) < 20) m.leaving = true;
  }

  clearMonsters() {
    for (let i = this.mons.length - 1; i >= 0; i--) this.removeMon(i);
  }
}
