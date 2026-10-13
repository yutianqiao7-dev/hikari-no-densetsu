import * as THREE from 'three';
import { Monster, angDiff } from '../actors/actor.js';
import { MONSTERS } from './data.js';
import { ISLANDS } from '../world/world.js';

const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const DRAGON_SCALE = 1.35;
const CRUISE = 42;          // 海の上を飛ぶ高さ
const WORLD_R = 2100;       // これより遠くへは行けない（海の果て）
// 鞍の上の座席（竜のローカル座標・拡大前）。前から順に
const SEATS = [V(0, 3.38, 0.95), V(0, 3.42, 0.38), V(0, 3.38, -0.2), V(0, 3.28, -0.78)];

/**
 * 竜ヴァルザードに乗って海の上を飛ぶ。
 * スティックの向きへ旋回しながら進み、島の上で A を押すと着地する。
 * 着地した島では竜がその場で待っていて、話しかけると また飛び立てる。
 */
export class Flight {
  constructor(g) {
    this.g = g;
    this.dragon = null;
    this.parked = null;       // { map, pos, rot }：島で待っている竜
    this.pos = V();
    this.heading = 0;
    this.speed = 0;
    this.bank = 0;
    this.flap = 0;
    this.cam = { yaw: 0, pitch: 0.28, lastManual: -99 };
    this.hint = document.createElement('div');
    this.hint.className = 'flight-hint hidden';
    g.ui.root.appendChild(this.hint);
    this.landing = null;
  }

  ensureDragon() {
    if (this.dragon) return this.dragon;
    const d = new Monster(this.g.world.lib, { ...MONSTERS.dragon, scale: DRAGON_SCALE });
    d.root.visible = false;
    d.ride = true;
    if (d.parts.BackSpikes) d.parts.BackSpikes.visible = false;
    if (d.parts.Saddle) d.parts.Saddle.visible = true;
    this.g.scene.add(d.root);
    this.dragon = d;
    return d;
  }

  /** 島で待っている竜を置く（いまの島の座標） */
  park(mapId, pos, rot) {
    const d = this.ensureDragon();
    this.parked = { map: mapId, pos: pos.clone(), rot };
    d.root.position.copy(pos);
    d.root.rotation.set(0, rot, 0);
  }

  /** 毎フレーム：待っている竜の表示 */
  updateParked(dt) {
    const d = this.dragon, p = this.parked, g = this.g;
    if (!d || this.active) return;
    const show = !!p && p.map === g.world.map.id && g.field.inField && !g.world.sea && g.field.visibleAll !== false
      && (g.mode === 'field' || g.mode === 'cutscene');
    d.root.visible = show;
    if (!show) return;
    d.root.position.copy(p.pos);
    d.root.position.y = g.field.env.height(p.pos.x, p.pos.z);
    d.update(dt);
  }

  riders() {
    const f = this.g.field, s = this.g.state;
    return s.party.filter((m) => m.hp > 0).map((m) => f.modelOf(m)).filter(Boolean).slice(0, SEATS.length);
  }

  /** 竜に乗って飛び立つ */
  async takeoff() {
    const g = this.g, f = g.field, w = g.world;
    if (g.mode !== 'field' || !f.inField) return;
    g.mode = 'cutscene';
    g.audio.sfx('roar');
    await g.ui.fadeTo(1, 600);
    // ほかの島を読み込む
    const ids = Object.keys(ISLANDS).filter((k) => !w.maps[k]);
    if (ids.length) {
      g.ui.showBanner('うみの むこうを ながめている…');
      for (const k of ids) { try { await w.ensureMap(k); } catch (e) { console.warn('island load failed', k, e); } }
    }
    const d = this.ensureDragon();
    const [ox, oz] = w.map.isl.offset;
    const base = this.parked && this.parked.map === w.map.id ? this.parked.pos : f.pos;
    this.pos.set(base.x + ox, f.env.height(base.x, base.z) + 2, base.z + oz);
    this.heading = this.parked && this.parked.map === w.map.id ? this.parked.rot : f.facing;
    this.parked = null;
    this.speed = 0;
    this.cam.yaw = this.heading + Math.PI;
    this.alt = this.pos.y;
    this.climb = 1;
    f.clearMonsters();
    f.setVisible(false);
    for (const h of Object.values(f.followers)) h.root.visible = false;
    for (const c of Object.values(f.coffins || {})) c.root.visible = false;
    f.hero.root.visible = false;
    w.enterSea();
    d.root.visible = true;
    this.active = true;
    for (const h of this.riders()) { h.root.visible = true; h.speed = 0; h.play(h.has && h.has('Ride') ? 'Ride' : 'Idle', { loop: true, fade: 0.01 }); }
    g.hud.setVisible(false);
    g.mode = 'flight';
    this.place(0);
    g.audio.play('flight', { fade: 1 });
    await g.ui.fadeTo(0, 700);
    g.ui.showBanner('ヴァルザードの せなか');
  }

  /** 竜とライダーの位置・カメラ（dt=0 でスナップ） */
  place(dt) {
    const d = this.dragon, g = this.g;
    d.root.position.copy(this.pos);
    d.root.rotation.set(this.pitch || 0, this.heading, -this.bank * 0.55, 'YXZ');
    d.root.updateMatrixWorld(true);
    const q = d.root.quaternion;
    this.riders().forEach((h, i) => {
      const seat = d.root.localToWorld(SEATS[i].clone());
      h.root.quaternion.copy(q);
      h.root.position.copy(seat).add(V(0, -0.92, 0).applyQuaternion(q));
      h.update(dt || 0.016);
    });
    // カメラ：竜の後ろ上から
    const c = this.cam;
    const fwd = V(Math.sin(this.heading), 0, Math.cos(this.heading));
    const dist = 26, yaw = c.yaw, pitch = c.pitch;
    const want = this.pos.clone().add(V(Math.sin(yaw) * Math.cos(pitch) * dist, Math.sin(pitch) * dist + 6, Math.cos(yaw) * Math.cos(pitch) * dist));
    const look = this.pos.clone().addScaledVector(fwd, 8).add(V(0, 4, 0));
    const cam = g.camera;
    if (!dt) cam.position.copy(want); else cam.position.lerp(want, Math.min(1, dt * 4));
    cam.lookAt(look);
  }

  update(dt) {
    const g = this.g, w = g.world, d = this.dragon;
    const busy = g.ui.busy;
    const mv = g.input.poll(dt, busy);
    const ic = g.input.cam;
    const c = this.cam;
    if (ic.yaw || ic.pitch) c.lastManual = g.t;
    c.yaw += ic.yaw;
    c.pitch = THREE.MathUtils.clamp(c.pitch + ic.pitch, 0.02, 0.9);
    ic.yaw = ic.pitch = ic.zoom = 0;

    // 操作：スティックの向き（カメラ基準）へ旋回して進む
    let targetSpeed = 9;
    let turn = 0;
    if (!busy && mv.len > 0.08 && !this.landing) {
      const yaw = c.yaw;
      const fx = -Math.sin(yaw), fz = -Math.cos(yaw), rx = Math.cos(yaw), rz = -Math.sin(yaw);
      const dx = fx * -mv.y + rx * mv.x, dz = fz * -mv.y + rz * mv.x;
      const target = Math.atan2(dx, dz);
      turn = angDiff(this.heading, target);
      this.heading += turn * Math.min(1, dt * 1.5);
      targetSpeed = 22 + 30 * mv.len * Math.max(0.35, Math.cos(Math.min(Math.abs(turn), 1.4)));
    }
    if (this.landing) targetSpeed = 0;
    this.speed += (targetSpeed - this.speed) * Math.min(1, dt * 1.2);
    this.bank += (THREE.MathUtils.clamp(turn * 0.9, -0.7, 0.7) - this.bank) * Math.min(1, dt * 3);
    const fwd = V(Math.sin(this.heading), 0, Math.cos(this.heading));
    this.pos.addScaledVector(fwd, this.speed * dt);
    // 海の果て
    const r = Math.hypot(this.pos.x, this.pos.z);
    if (r > WORLD_R) { this.pos.x *= WORLD_R / r; this.pos.z *= WORLD_R / r; }

    // 高さ：島の上は地面より上を保つ
    const isl = w.islandAt(this.pos.x, this.pos.z);
    const ahead = w.islandAt(this.pos.x + fwd.x * 40, this.pos.z + fwd.z * 40);
    const ground = Math.max(0, isl ? isl.h : 0, ahead ? ahead.h : 0);
    let alt = Math.max(CRUISE, ground + 26);
    if (this.landing) alt = this.landing.y;
    const prevY = this.pos.y;
    this.pos.y += (alt - this.pos.y) * Math.min(1, dt * (this.landing ? 1.6 : 0.8));
    this.pitch = THREE.MathUtils.clamp(-(this.pos.y - prevY) / Math.max(dt, 1e-3) * 0.02, -0.35, 0.35);

    // 羽ばたき（上昇中・速いときは速く）
    const climbing = this.pos.y < alt - 2;
    this.flap += dt * (climbing || this.landing ? 7.5 : this.speed > 30 ? 3.2 : 4.5);
    d.update(dt);
    const P = d.parts, rest = (o) => o.userData.rest;
    const amp = climbing || this.landing ? 0.75 : this.speed > 40 ? 0.22 : 0.45;
    const fl = Math.sin(this.flap) * amp;
    if (P.WingL) P.WingL.rotation.z = rest(P.WingL).r.z + fl + 0.1;
    if (P.WingR) P.WingR.rotation.z = rest(P.WingR).r.z - fl - 0.1;
    d.root.position.y += Math.cos(this.flap) * 0.25;

    // カメラは操作していないと竜の後ろへ戻る
    if (g.t - c.lastManual > 1.5) c.yaw += angDiff(c.yaw, this.heading + Math.PI) * Math.min(1, dt * 0.8);
    this.place(dt);

    // 着地できる場所の案内
    this.canLand = null;
    if (isl && !this.landing) {
      const lx = isl.lx, lz = isl.lz;
      const ok = isl.h > 1.2 && isl.map.hf.slope(lx, lz) < 0.5 && !isl.map.env.areaAt(lx, lz);
      const barrier = isl.map.id === 'dark' && !g.state.flags.darkOpen;
      if (ok && !barrier) this.canLand = isl;
      if (barrier && !this._barrierT) this.barrier();
    }
    this.hint.classList.toggle('hidden', !!busy || !!this.landing || !this.canLand);
    if (this.canLand) this.hint.textContent = `A：${this.canLand.map.isl.name}に おりる`;
    // 近くの島の名前
    const near = isl ? isl.map.isl.name : null;
    if (near !== this.lastIsl) { this.lastIsl = near; if (near) g.ui.showBanner(near); }
    g.sky.update(dt, this.pos, g.camera);
  }

  /** 闇の島の結界：はじき返される */
  async barrier() {
    this._barrierT = true;
    const g = this.g;
    this.heading += Math.PI;
    this.pos.addScaledVector(V(Math.sin(this.heading), 0, Math.cos(this.heading)), 30);
    g.audio.sfx('miss');
    g.ui.flashScreen('#a040ff', 300, 0.35);
    await g.ui.say([{ who: 'ヴァルザード', text: 'ぐっ……！ やみの けっかいが はられている。 いまの われらでは ちかづけぬ。' },
      { who: 'ヴァルザード', text: 'のこる 三つの しまの 「せいれいの ほうじゅ」を あつめれば、 けっかいを やぶれるはずだ。' }]);
    this._barrierT = false;
  }

  onKey(k) {
    const g = this.g;
    if (g.ui.busy) { g.ui.key(k); return; }
    if (k === 'confirm' && this.canLand) this.land(this.canLand);
    else if (k === 'menu' || k === 'cancel') this.flightMenu();
  }

  async flightMenu() {
    const g = this.g;
    const i = await g.ui.choose([{ label: 'おりる', disabled: !this.canLand }, { label: 'ちず' }, { label: 'とじる' }], { right: 'calc(14px + var(--sar) + var(--btnw))', top: 'calc(min(170px, 36vh) + var(--sat))', title: 'ヴァルザード' });
    if (i === 0 && this.canLand) this.land(this.canLand);
    if (i === 1) await this.showMap();
  }

  /** 海の地図：島の位置と自分 */
  async showMap() {
    const g = this.g, s = g.state;
    const lines = Object.entries(ISLANDS).map(([k, v]) => {
      const dx = v.offset[0] - this.pos.x, dz = v.offset[1] - this.pos.z;
      const dist = Math.round(Math.hypot(dx, dz) / 10) * 10;
      const ang = Math.atan2(dx, -dz);
      const dirs = ['きた', 'ほくとう', 'ひがし', 'なんとう', 'みなみ', 'なんせい', 'にし', 'ほくせい'];
      const di = dirs[((Math.round(ang / (Math.PI / 4)) % 8) + 8) % 8];
      const done = s.flags['orb_' + k] ? '（ほうじゅ かくとく）' : '';
      return `${v.name}：${dist < 60 ? 'すぐ そば' : `${di}へ ${dist}m`}${done}`;
    });
    await g.ui.say([{ who: 'うみの ちず', text: lines.join('\n') }]);
  }

  /** 島に着地する */
  async land(isl) {
    const g = this.g, w = g.world, f = g.field;
    if (this.landing) return;
    // 着地点：竜の真下の近くで、歩けて平らな場所
    const map = isl.map;
    let best = null;
    for (let r = 0; r < 30 && !best; r += 3) {
      for (let k = 0; k < 12; k++) {
        const a = k / 12 * Math.PI * 2;
        const lx = isl.lx + Math.cos(a) * r, lz = isl.lz + Math.sin(a) * r;
        const h = map.hf.height(lx, lz);
        if (h > 1.2 && map.hf.slope(lx, lz) < 0.45 && !map.env.areaAt(lx, lz) && map.env.walkable(lx, lz, h)) { best = { lx, lz, h }; break; }
      }
    }
    if (!best) { g.ui.showBanner('ここには おりられない'); return; }
    this.landing = { y: best.h + 8 };
    const [ox, oz] = map.isl.offset;
    const target = V(best.lx + ox, best.h, best.lz + oz);
    // ゆっくり降りる
    const t0 = performance.now();
    const from = this.pos.clone();
    await new Promise((res) => {
      const step = () => {
        const k = Math.min(1, (performance.now() - t0) / 2600);
        this.pos.x = from.x + (target.x - from.x) * k;
        this.pos.z = from.z + (target.z - from.z) * k;
        this.landing.y = from.y + (target.y + 0.3 - from.y) * (1 - Math.pow(1 - k, 2));
        if (k < 1) requestAnimationFrame(step); else res();
      };
      step();
    });
    g.mode = 'cutscene';
    await g.ui.fadeTo(1, 600);
    this.active = false;
    this.landing = null;
    this.hint.classList.add('hidden');
    for (const h of this.riders()) h.stopOneShot(0.01);
    w.useMap(map.id);
    g.hud.buildBaseMap(w);
    f.setEnv(w.fieldEnv);
    f.refreshMapPoints();
    const fwd = V(Math.sin(this.heading), 0, Math.cos(this.heading));
    const right = V(fwd.z, 0, -fwd.x);
    // 勇者は竜の横に降りる（カメラが竜にめり込まないように）
    let hp = null;
    for (const side of [1, -1]) {
      for (const dist of [10, 8, 12, 6]) {
        const c = V(best.lx, 0, best.lz).addScaledVector(right, side * dist).addScaledVector(fwd, 3);
        if (!hp && map.env.walkable(c.x, c.z, best.h)) hp = c;
      }
    }
    if (!hp) hp = V(best.lx, 0, best.lz).addScaledVector(fwd, 9);
    this.park(map.id, V(best.lx, best.h, best.lz), this.heading);
    f.place(hp, this.heading);
    f.setVisible(true);
    g.state.flags['visit_' + map.id] = true;
    g.mode = 'field';
    g.hud.setVisible(true);
    g.hud.update();
    f.area = undefined;
    g.updateMusic(true);
    await g.ui.fadeTo(0, 700);
    g.ui.showBanner(map.isl.name);
    if (g.story.onLand) g.story.onLand(map.id);
  }
}
