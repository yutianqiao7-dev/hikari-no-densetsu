import * as THREE from 'three';
import { Humanoid, Monster, angDiff } from '../actors/actor.js';
import { MONSTERS } from './data.js';
import { AREAS } from '../world/world.js';

const NPC_MODELS = {
  King: 'King', Guard1: 'Guard', Guard2: 'Guard', Guard3: 'Guard', Guard4: 'Guard', Minister: 'Minister',
  Innkeeper: 'Innkeeper', Merchant: 'Merchant', Elder: 'Elder', Girl: 'Girl', Villager1: 'Villager', Villager2: 'Villager',
};
const WANDER = new Set(['Girl', 'Villager1', 'Villager2', 'Minister']);

/**
 * 勇者の操作・カメラ・NPC・徘徊モンスター・話しかけ。
 * 現在いる場所（フィールド／ダンジョンの各フロア）は env で切り替える。
 */
export class Field {
  constructor(game) {
    this.g = game;
    const { world, scene } = game;
    this.world = world;
    this.scene = scene;
    this.camera = game.camera;
    this.env = world.fieldEnv;

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
    this.signs = ['Sign1', 'Sign2', 'Sign3', 'Sign4'].map((id) => world.marker(id) && { id, pos: world.marker(id).pos }).filter(Boolean);
    this.doors = [
      { id: 'cave', m: world.marker('CaveEntrance') },
      { id: 'tower', m: world.marker('TowerDoor') },
    ].filter((d) => d.m);

    // 魔竜（まおうの塔 3F）・がんせきの番人（洞窟 B2）
    this.boss = new Monster(world.lib, MONSTERS.dragon);
    this.boss.root.visible = false;
    scene.add(this.boss.root);
    this.guardian = new Monster(world.lib, MONSTERS.guardian);
    this.guardian.root.visible = false;
    scene.add(this.guardian.root);

    // シンボルエンカウントのモンスター
    this.mons = [];
    this.spawnT = 0;
    this.safeT = 0;
    this.stepT = 0;
    this.area = null;
    this.nearDoor = null;
    this.hint = document.createElement('div');
    this.hint.className = 'talk-hint hidden';
    game.ui.root.appendChild(this.hint);
  }

  get inField() { return this.env.kind === 'field'; }

  /** 場所の切り替え */
  setEnv(env) {
    this.env = env;
    this.clearMonsters();
    const field = env.kind === 'field';
    for (const n of this.npcs) n.h.root.visible = field;
    this.placeBosses();
  }

  placeBosses() {
    const env = this.env, fl = this.g.state ? this.g.state.flags : {};
    const at = (spot) => {
      const s = env.spots && env.spots[spot];
      if (!s) return null;
      const x = s.reduce((a, p) => a + p[0], 0) / s.length, z = s.reduce((a, p) => a + p[1], 0) / s.length;
      return new THREE.Vector3(x, 0, z);
    };
    const bp = env.id === 'tower3' ? at('B') : null;
    this.boss.root.visible = !!bp && !fl.cleared;
    if (bp) { this.boss.root.position.copy(bp).add(new THREE.Vector3(0, 0, -1)); this.boss.root.rotation.y = 0; }
    const gp = env.id === 'cave2' ? at('B') : null;
    this.guardian.root.visible = !!gp && !fl.guardian;
    if (gp) { this.guardian.root.position.copy(gp); this.guardian.root.rotation.y = Math.PI; }
    this.bossPos = bp;
    this.guardianPos = gp;
  }

  place(pos, rot) {
    this.pos.copy(pos);
    this.pos.y = this.env.height(pos.x, pos.z);
    this.facing = rot;
    this.cam.yaw = rot + Math.PI;
    this.vel.set(0, 0, 0);
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
    for (const n of this.npcs) n.h.root.visible = v && this.inField;
    for (const m of this.mons) m.root.visible = v;
    if (v) this.placeBosses();
    else { this.boss.root.visible = this.guardian.root.visible = false; }
    if (!v) this.hint.classList.add('hidden');
  }

  // ------------------------------------------------------------ 毎フレーム
  update(dt, t, mv, inputCam) {
    const env = this.env;
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
      if (!this.inField) speed = Math.min(speed, 6.0);
      const d = Math.hypot(dx, dz);
      dx /= d; dz /= d;
      const target = Math.atan2(dx, dz);
      this.facing += angDiff(this.facing, target) * Math.min(1, dt * 12);
    }
    const want = new THREE.Vector3(dx * speed, 0, dz * speed);
    this.vel.lerp(want, Math.min(1, dt * (speed > 0 ? 10 : 14)));
    const next = this.pos.clone().addScaledVector(this.vel, dt);
    if (env.walkable(next.x, next.z, this.pos.y)) {
      env.colliders.resolve(next, 0.42);
      if (this.inField) for (const n of this.npcs) this.pushOut(next, n.pos, 0.85);
      if (this.boss.root.visible) this.pushOut(next, this.boss.root.position, 4.0);
      if (this.guardian.root.visible) this.pushOut(next, this.guardian.root.position, 2.2);
      if (env.walkable(next.x, next.z, this.pos.y)) { this.pos.x = next.x; this.pos.z = next.z; }
    } else {
      // 壁・斜面・水際ではすべるように
      if (env.walkable(next.x, this.pos.z, this.pos.y)) this.pos.x = next.x;
      else if (env.walkable(this.pos.x, next.z, this.pos.y)) this.pos.z = next.z;
      this.vel.multiplyScalar(0.5);
    }
    const gy = env.height(this.pos.x, this.pos.z);
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
        if (this.hero.speed > 3.6) this.g.fx.emit({ pos: this.pos.clone().add(new THREE.Vector3(0, 0.1, 0)), count: 3, color: this.inField ? 0xb8a888 : 0x6a625a, speed: 0.6, up: 0.4, life: 0.7, size: 0.35, grow: 1.5, drag: 2 });
      }
    }

    // カメラの自動追従
    if (this.hero.speed > 2 && t - this.cam.lastManual > 1.6) {
      this.cam.yaw += angDiff(this.cam.yaw, this.facing + Math.PI) * Math.min(1, dt * 0.9);
    }
    this.updateCamera(dt);

    // NPC・ボス
    if (this.inField) for (const n of this.npcs) this.updateNpc(n, dt);
    if (this.boss.root.visible) this.boss.update(dt);
    if (this.guardian.root.visible) this.guardian.update(dt);

    if (this.inField) {
      // エリア名と BGM
      const area = env.areaAt(this.pos.x, this.pos.z);
      if (area !== this.area) {
        this.area = area;
        if (area) this.g.ui.showBanner(AREAS[area].name);
        this.g.updateMusic();
      }
      // 洞窟の入口・塔の扉
      let near = null;
      for (const d of this.doors) if (Math.hypot(this.pos.x - d.m.pos.x, this.pos.z - d.m.pos.z) < 1.9) near = d.id;
      if (near && near !== this.nearDoor) { this.nearDoor = near; this.g.onDoor(near); return; }
      this.nearDoor = near;
    } else {
      const tr = env.trigger(this.pos.x, this.pos.z);
      if (tr) { this.g.onTrigger(tr); return; }
    }

    this.updateMonsters(dt, t);
    this.updateHint();
  }

  pushOut(p, c, r) {
    const dx = p.x - c.x, dz = p.z - c.z, d = Math.hypot(dx, dz);
    if (d < r && d > 1e-4) { p.x = c.x + (dx / d) * r; p.z = c.z + (dz / d) * r; }
  }

  updateCamera(dt, snap = false) {
    const c = this.cam, env = this.env;
    const tgt = this.pos.clone().add(new THREE.Vector3(0, 1.35, 0));
    c.target.lerp(tgt, snap ? 1 : Math.min(1, dt * 8));
    // ダンジョンでは壁越しに見下ろす角度・距離に制限
    const pitch = this.inField ? c.pitch : Math.max(c.pitch, 0.95);
    const dist = this.inField ? c.dist : Math.min(c.dist, 11);
    const cp = Math.cos(pitch), sp = Math.sin(pitch);
    const want = c.target.clone().add(new THREE.Vector3(Math.sin(c.yaw) * cp * dist, sp * dist + 0.4, Math.cos(c.yaw) * cp * dist));
    if (this.inField) {
      // 木の葉の中にカメラが入らないよう、樹冠に当たったら手前に寄せる
      const dirv = want.clone().sub(c.target);
      const full = dirv.length();
      dirv.divideScalar(full);
      let lim = full;
      for (let k = 1; k <= 12; k++) {
        const d = (k / 12) * full;
        const q = c.target.clone().addScaledVector(dirv, d);
        for (const t of env.colliders.near(q.x, q.z)) {
          if (!t.tree) continue;
          const cy = t.y + 4.2 * t.tree, cr = 2.6 * t.tree;
          const dx = q.x - t.x, dz = q.z - t.z, dy = (q.y - cy) * 1.3;
          if (dx * dx + dz * dz + dy * dy < cr * cr) { lim = Math.min(lim, Math.max(2.2, d - 0.8)); break; }
        }
        if (lim < full) break;
      }
      if (lim < full) want.copy(c.target).addScaledVector(dirv, lim);
    }
    const gh = env.height(want.x, want.z) + 0.6;
    if (want.y < gh) want.y = gh;
    this.camPos.lerp(want, snap ? 1 : Math.min(1, dt * 10));
    this.camera.position.copy(this.camPos);
    this.camera.lookAt(c.target);
  }

  updateNpc(n, dt) {
    const h = n.h, w = this.world;
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
          if (w.colliders.resolve(nx, 0.4)) n.target = null;
          if (nx.distanceTo(this.pos) > 1.0) n.pos.copy(nx);
          n.pos.y = w.hf.height(n.pos.x, n.pos.z);
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
    h.root.visible = this.visibleAll !== false && this.inField && d2 < 95 * 95;
    if (d2 < 70 * 70) h.update(dt);
  }

  /** 前方の話しかけられる相手・調べられる物 */
  findInteract() {
    let best = null, bd = 99;
    const fwd = new THREE.Vector3(Math.sin(this.facing), 0, Math.cos(this.facing));
    const fl = this.g.state ? this.g.state.flags : {};
    const check = (id, p, range, kind, obj = null) => {
      const d = new THREE.Vector3().subVectors(p, this.pos);
      d.y = 0;
      const dist = d.length();
      if (dist > range) return;
      if (dist > 0.8 && d.normalize().dot(fwd) < 0.2) return;
      if (dist < bd) { bd = dist; best = { id, kind, obj, pos: p }; }
    };
    if (this.inField) {
      for (const n of this.npcs) check(n.id, n.pos, 3.0, 'npc', n);
      for (const s of this.signs) check(s.id, s.pos, 2.4, 'sign');
    } else {
      const env = this.env;
      for (const c of env.chests) if (!(fl.chests && fl.chests[c.id])) check(c.id, c.pos, 2.4, 'chest', c);
      if (env.orb && env.orb.visible) check('orb', env.orb.getWorldPosition(new THREE.Vector3()).setY(0), 2.8, 'orb');
      if (this.guardian.root.visible) check('guardian', this.guardian.root.position, 5.5, 'guardian');
      if (this.boss.root.visible) check('Boss', this.boss.root.position, 10, 'boss');
    }
    return best;
  }

  updateHint() {
    const it = this.g.ui.busy ? null : this.findInteract();
    if (!it) { this.hint.classList.add('hidden'); return; }
    const hy = { sign: 2.4, boss: 6, guardian: 4.2, chest: 1.6, orb: 2.4 }[it.kind] || 2.2;
    const p = it.pos.clone().add(new THREE.Vector3(0, hy, 0)).project(this.camera);
    if (p.z > 1) { this.hint.classList.add('hidden'); return; }
    this.hint.classList.remove('hidden');
    this.hint.textContent = { sign: 'しらべる', boss: 'たちむかう', guardian: 'たちむかう', chest: 'あける', orb: 'しらべる' }[it.kind] || 'はなす';
    this.hint.style.left = ((p.x + 1) / 2) * window.innerWidth + 'px';
    this.hint.style.top = ((1 - p.y) / 2) * window.innerHeight + 'px';
  }

  // ------------------------------------------------------------ モンスター
  updateMonsters(dt) {
    const env = this.env;
    const night = this.g.sky.night > 0.5;
    this.safeT = Math.max(0, this.safeT - dt);
    const inSafe = this.inField && !!this.area && this.area !== 'tower';
    const maxMons = this.inField ? 7 : 5;
    this.spawnT -= dt;
    if (this.spawnT <= 0 && this.mons.length < maxMons) {
      this.spawnT = this.inField ? 1.2 : 2.0;
      const sp = env.spawnPoint(this.pos);
      if (sp) {
        const tab = env.encounter(sp.x, sp.z, night);
        const key = tab.list[Math.floor(Math.random() * tab.list.length)];
        const m = new Monster(this.world.lib, MONSTERS[key]);
        m.key = key;
        m.lv = tab.lv;
        m.root.position.set(sp.x, sp.y, sp.z);
        m.heading = Math.random() * Math.PI * 2;
        m.state = 'wander';
        m.wait = Math.random() * 2;
        m.setOpacity(0);
        m.fadeIn = 0;
        this.scene.add(m.root);
        this.mons.push(m);
      }
    }
    const range = this.inField ? 95 : 60;
    for (let i = this.mons.length - 1; i >= 0; i--) {
      const m = this.mons[i];
      const p = m.root.position;
      const toP = new THREE.Vector3().subVectors(this.pos, p);
      toP.y = 0;
      const dist = toP.length();
      if (dist > range || (m.leaving && m.opacity <= 0.01)) { this.removeMon(i); continue; }
      if (m.fadeIn < 1 && !m.leaving) { m.fadeIn = Math.min(1, m.fadeIn + dt * 1.5); m.setOpacity(m.fadeIn); }
      if (m.leaving) m.setOpacity(Math.max(0, m.opacity - dt * 1.5));
      let sp = 0;
      const fast = m.kind === 'Bat' ? 5.2 : m.kind === 'Golem' ? 2.6 : m.kind === 'Ghost' ? 3.8 : 4.0;
      if (!inSafe && this.safeT <= 0 && dist < (this.inField ? 15 : 11) && !m.leaving) {
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
        if (env.monsterOK(nx, nz)) {
          const np = new THREE.Vector3(nx, 0, nz);
          env.colliders.resolve(np, 0.5);
          p.x = np.x; p.z = np.z;
        } else m.heading += Math.PI * 0.7;
      }
      p.y += (env.height(p.x, p.z) - p.y) * Math.min(1, dt * 10);
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
