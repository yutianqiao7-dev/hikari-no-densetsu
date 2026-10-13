import * as THREE from 'three';
import { Monster } from '../actors/actor.js';
import { MONSTERS, SPELLS, ITEMS, MEMBERS } from './data.js';
import { derived, knownSpells, gainExp, memberName } from './state.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rnd = (a, b) => a + Math.random() * (b - a);
const rint = (a, b) => Math.floor(rnd(a, b + 1));
const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

/**
 * パーティ戦闘（その場のフィールドで 3D）。
 * opts: { symbol: 野外のモンスター, boss: 'dragon'|'guardian', group: [モンスターキー], noFlee, intro }
 */
export class Battle {
  constructor(game, opts) {
    this.g = game;
    this.f = game.field;
    this.opts = opts;
    this.s = game.state;
    this.enemies = [];
    this.allies = [];
    this.shake = 0;
    this.camPos = game.camera.position.clone();
    this.camLook = this.f.cam.target.clone();
    this.shot = null;
    this.arrow = null;
  }

  // ------------------------------------------------------------ 準備
  setup() {
    const f = this.f, env = f.env;
    const heroPos = f.pos.clone();
    let dir;
    const boss = this.opts.boss;
    if (boss) {
      this.bossObj = boss === 'dragon' ? f.boss : boss === 'guardian' ? f.guardian : f.ibossObj;
      const bp = this.bossObj.root.position;
      dir = V(bp.x - heroPos.x, 0, bp.z - heroPos.z).normalize();
      this.bigB = this.isBigKind(this.bossObj.kind);
      heroPos.copy(bp).addScaledVector(dir, this.bigB ? -12.5 * (this.bossObj.def.scale || 1.15) / 1.15 : -(6 + 1.2 * (this.bossObj.def.scale || 1)));
    } else if (this.opts.symbol) {
      const sp = this.opts.symbol.root.position;
      dir = V(sp.x - heroPos.x, 0, sp.z - heroPos.z);
      if (dir.lengthSq() < 0.01) dir.set(Math.sin(f.facing), 0, Math.cos(f.facing));
      dir.normalize();
    } else dir = V(Math.sin(f.facing), 0, Math.cos(f.facing));
    if (!f.inField && !boss) {
      const best = this.roomyLine(heroPos, dir);
      heroPos.copy(best.p);
      dir = best.d;
    }
    heroPos.y = env.height(heroPos.x, heroPos.z);
    this.dir = dir;
    this.right = V(dir.z, 0, -dir.x);
    this.center0 = heroPos.clone();
    f.pos.copy(heroPos);
    f.facing = Math.atan2(dir.x, dir.z);

    // 味方の隊列（横一列、中央が少し前）。たおれている仲間は棺桶になって後ろへ
    const party = this.s.party;
    const n = party.length;
    const ordered = [...party.filter((m) => m.hp > 0), ...party.filter((m) => m.hp <= 0)];
    this.deadOrder = [];
    let gap = f.inField ? 1.8 : 1.45;
    // 屋内のせまい通路では横一列に入りきらないので、間をつめるか2列にする
    let rows = 1;
    if (!f.inField && n > 1) {
      const halfW = Math.min(this.freeDist(heroPos, this.right, 4), this.freeDist(heroPos, this.right.clone().negate(), 4));
      const fit = (halfW - 0.45) * 2 / (n - 1);
      if (fit < 1.0) rows = 2;
      else gap = Math.min(gap, fit);
      if (rows === 2) gap = Math.max(0.9, Math.min(1.3, (halfW - 0.4) * 2 / (Math.ceil(n / 2) - 1 || 1)));
    }
    const perRow = rows === 2 ? Math.ceil(n / 2) : n;
    this.rows = rows;
    party.forEach((m) => {
      const h = m.id === 'hero' ? f.hero : f.followerOf(m.id);
      if (!h) return;
      const i = ordered.indexOf(m);
      const row = Math.floor(i / perRow), col = i % perRow, cnt = row === 0 ? perRow : n - perRow;
      const lat = (col - (cnt - 1) / 2) * gap + (row === 1 ? gap * 0.25 : 0);
      const home = heroPos.clone().addScaledVector(this.right, lat).addScaledVector(dir, -Math.abs(lat) * 0.25 - row * 1.7);
      home.y = env.height(home.x, home.z);
      h.root.visible = true;
      h.root.position.copy(home);
      h.root.rotation.y = f.facing;
      h.speed = 0;
      if (m.id === 'hero') h.setWeapon(true);
      const a = { m, h, home, home0: home.clone(), name: memberName(this.s, m), defending: false };
      this.allies.push(a);
      if (m.hp <= 0) {
        h.root.visible = false;
        a.coffin = f.coffinOf(m.id);
        this.deadOrder.push(a);
      }
    });
    this.placeCoffins(true);

    // 敵の編成
    if (boss) {
      const m = this.bossObj;
      this.enemies.push(this.makeEnemy(boss, m, m.root.position.clone()));
    } else {
      let keys;
      if (this.opts.group) keys = this.opts.group.slice();
      else {
        const sym = this.opts.symbol;
        const tab = env.encounter(heroPos.x, heroPos.z, this.g.sky.night > 0.5);
        keys = [sym.key];
        const extra = Math.random() < 0.7 ? rint(0, Math.min(2 + (n > 2 ? 1 : 0), tab.lv >= 3 ? 3 : 1)) : 0;
        for (let i = 0; i < extra; i++) keys.push(Math.random() < 0.55 ? sym.key : pick(tab.list));
        f.removeMonster(sym);
      }
      const ne = keys.length;
      const front = (f.inField ? 6.6 : 5.6) + (ne > 3 ? 1 : 0);
      keys.forEach((k, i) => {
        const lat = (i - (ne - 1) / 2) * (f.inField ? 2.8 : 2.1);
        let p;
        for (let k = 1; k > 0.2; k -= 0.15) {
          p = heroPos.clone().addScaledVector(dir, (front + Math.abs(lat) * 0.22) * (0.7 + 0.3 * k)).addScaledVector(this.right, lat * k);
          if (f.inField || this.clearAt(p, 0.9)) break;
        }
        p.y = env.height(p.x, p.z);
        const mon = new Monster(this.g.world.lib, MONSTERS[k]);
        mon.root.position.copy(p);
        mon.root.rotation.y = Math.atan2(-dir.x, -dir.z);
        this.g.scene.add(mon.root);
        this.enemies.push(this.makeEnemy(k, mon, p));
      });
    }
    const count = {};
    for (const e of this.enemies) count[e.key] = (count[e.key] || 0) + 1;
    const idx = {};
    for (const e of this.enemies) {
      if (count[e.key] > 1) { idx[e.key] = (idx[e.key] || 0) + 1; e.name = e.def.name + ' ' + 'ABCDE'[idx[e.key] - 1]; }
    }
    f.setVisible(false);
    for (const a of this.allies) a.h.root.visible = a.m.hp > 0;
    this.placeCoffins(true);
    if (boss) this.bossObj.root.visible = true;
    this.center = this.enemies.reduce((a, e) => a.add(e.home), V()).multiplyScalar(1 / this.enemies.length);
    // 戦いの場の周りの木・岩を消して、カメラの邪魔にならないように
    const mid = this.center.clone().lerp(this.center0, 0.5);
    const rad = this.center.distanceTo(this.center0) * 0.5 + (this.bigB ? 22 : 15);
    this.g.world.veg.setExclude(mid, rad);
    this.fitCam = this.g.camera.clone();
  }

  /** 棺桶の置き場所（味方の列のうしろに横並び） */
  coffinSlot(k, total) {
    let back = (this.rows || 1) * 1.7 + (this.f.inField ? 3.9 : 1.2);
    const lat = (k - (total - 1) / 2) * 1.05;
    let p = this.center0.clone().addScaledVector(this.dir, -back).addScaledVector(this.right, lat);
    // 屋内では壁にめり込まない所まで前へ
    while (!this.f.inField && back > 0.8 && !this.f.env.walkable(p.x, p.z)) {
      back -= 0.4;
      p = this.center0.clone().addScaledVector(this.dir, -back).addScaledVector(this.right, lat * 0.8);
    }
    p.y = this.f.env.height(p.x, p.z);
    return p;
  }

  /** 棺桶を列のうしろへ（instant でなければ跳ねながら移動） */
  placeCoffins(instant) {
    const list = this.deadOrder, n = list.length;
    const jobs = list.map((a, k) => {
      const c = a.coffin;
      const to = this.coffinSlot(k, n);
      c.root.visible = true;
      c.root.rotation.set(0, this.f.facing, 0);
      if (instant) { c.root.position.copy(to); a.home = to.clone(); return Promise.resolve(); }
      const from = c.root.position.clone();
      a.home = to.clone();
      const t0 = performance.now(), dur = 260 + from.distanceTo(to) * 160;
      return new Promise((res) => {
        const step = () => {
          const k2 = Math.min(1, (performance.now() - t0) / dur);
          c.root.position.lerpVectors(from, to, k2);
          c.root.position.y += Math.abs(Math.sin(k2 * Math.PI * Math.max(1, Math.round(dur / 220)))) * 0.25;
          if (k2 < 1) requestAnimationFrame(step); else { c.root.position.copy(to); res(); }
        };
        step();
      });
    });
    return Promise.all(jobs);
  }

  /** たおれた仲間を棺桶に入れて列のうしろへ */
  async coffinize(a) {
    if (a.coffin && a.coffin.root.visible) return;
    await sleep(450);
    const c = this.f.coffinOf(a.m.id);
    a.coffin = c;
    const p = a.h.root.position.clone();
    this.g.fx.emit({ pos: p.clone().add(V(0, 0.8, 0)), count: 40, color: [0xffffff, 0xd8d0ff], speed: 1.6, up: 1, life: 0.7, size: 0.45, grow: 1.2, drag: 1.5, spread: 0.6 });
    this.g.audio.sfx('miss');
    a.h.root.visible = false;
    c.root.position.copy(p);
    c.root.visible = true;
    this.deadOrder = this.deadOrder.filter((x) => x !== a);
    this.deadOrder.push(a);
    await this.placeCoffins(false);
  }

  /** 生きかえった仲間を棺桶から出して元の位置へ */
  uncoffin(a) {
    if (a.coffin) a.coffin.root.visible = false;
    this.deadOrder = this.deadOrder.filter((x) => x !== a);
    a.home = a.home0.clone();
    a.h.root.position.copy(a.home);
    a.h.root.rotation.y = this.f.facing;
    a.h.root.visible = true;
    a.h.stopOneShot(0.01);
    this.placeCoffins(false);
  }

  isBigKind(kind) { return kind === 'Dragon' || kind === 'Zenos' || kind === 'Ifrit'; }
  isBig(e) { return this.isBigKind(e.m.kind) || !!e.def.big; }

  /** p から向き d へ歩ける距離（屋内用） */
  freeDist(p, d, max) {
    const env = this.f.env;
    let s = 0;
    while (s < max && env.walkable(p.x + d.x * (s + 0.25), p.z + d.z * (s + 0.25))) s += 0.25;
    return s;
  }

  /** 半径 r の円が床の上に収まるか（屋内用） */
  clearAt(p, r) {
    const env = this.f.env;
    if (!env.walkable(p.x, p.z)) return false;
    for (let k = 0; k < 8; k++) {
      const a = k / 8 * Math.PI * 2;
      if (!env.walkable(p.x + Math.cos(a) * r, p.z + Math.sin(a) * r)) return false;
    }
    return true;
  }

  /** 屋内の戦闘：味方と敵が並べてカメラも引ける、いちばん広い向きと立ち位置を探す */
  roomyLine(p0, d0) {
    const env = this.f.env;
    const free = (p, d, max) => {
      let s = 0;
      while (s < max && env.walkable(p.x + d.x * (s + 0.5), p.z + d.z * (s + 0.5))) s += 0.5;
      return s;
    };
    const cands = [p0.clone()];
    if (env.cell) {
      const i = Math.floor((p0.x - env.ox) / env.cell), j = Math.floor((p0.z - env.oz) / env.cell);
      const [cx, cz] = env.center(i, j);
      cands.push(V(cx, p0.y, cz));
    }
    let best = { p: p0, d: d0, s: -1e9 };
    for (const p of cands) {
      if (!env.walkable(p.x, p.z)) continue;
      for (let k = 0; k < 16; k++) {
        const a = k / 16 * Math.PI * 2;
        const d = V(Math.sin(a), 0, Math.cos(a));
        const r = V(d.z, 0, -d.x);
        const m = p.clone().addScaledVector(d, 6);
        const ahead = Math.min(free(p, d, 11), 9);
        const back = Math.min(free(p, d.clone().negate(), 6), 5);
        const side = Math.min(free(m, r, 4), free(m, r.clone().negate(), 4));
        const side0 = Math.min(free(p, r, 3), free(p, r.clone().negate(), 3));
        const s = ahead + back * 0.8 + side * 1.3 + side0 * 0.8 + (d.dot(d0) > 0.9 ? 0.8 : 0) - p.distanceTo(p0) * 0.3;
        if (s > best.s) best = { p, d, s };
      }
    }
    return best;
  }

  /** 敵（と味方）の高さを含む注目点 */
  focusPoints(withAllies, actor) {
    const pts = [];
    for (const e of this.alive.length ? this.alive : this.enemies) {
      const h = this.isBig(e) ? 6.2 * (e.def.scale || 1.15) / 1.15 : ({ Bat: 2.2, Ghost: 2.2, Wisp: 2.4, Gargoyle: 2.6, Skeleton: 2.1, Crab: 1.2, Snake: 1.6, Scorpion: 1.8, Mummy: 2.0, Cactus: 1.6, Anubis: 2.9, Snowman: 1.9, Penguin: 1.5, Yeti: 2.6, Lizard: 1.1, Firebird: 2.3, EvilEye: 2.3, DarkKnight: 2.3 }[e.m.kind] || 1.9) * (e.def.scale || 1);
      const r = this.isBig(e) ? 3.2 : 0.7 * (e.def.scale || 1);
      pts.push(e.home.clone().addScaledVector(this.right, r), e.home.clone().addScaledVector(this.right, -r), e.home.clone().add(V(0, h, 0)), e.home.clone());
    }
    const allies = withAllies ? this.allies : actor ? [actor] : [];
    for (const a of allies) pts.push(a.home.clone(), a.home.clone().add(V(0, 2.0, 0)));
    return pts;
  }

  /** すべての注目点が画面の内側（上は敵名ウィンドウ、下はコマンド欄を避ける）に入るまでカメラを引く */
  fit(shot, pts) {
    const cam = this.fitCam;
    const src = this.g.camera;
    cam.fov = src.fov;
    cam.aspect = src.aspect;
    cam.updateProjectionMatrix();
    const dirv = shot.pos.clone().sub(shot.look);
    let dist = dirv.length();
    dirv.normalize();
    const v = V();
    for (let k = 0; k < 24; k++) {
      cam.position.copy(shot.look).addScaledVector(dirv, dist);
      cam.lookAt(shot.look);
      cam.updateMatrixWorld();
      let ok = true;
      for (const p of pts) {
        v.copy(p).project(cam);
        if (v.z > 1 || Math.abs(v.x) > 0.84 || v.y > 0.7 || v.y < -0.62) { ok = false; break; }
      }
      if (ok) break;
      dist *= 1.1;
    }
    shot.pos.copy(shot.look).addScaledVector(dirv, dist);
    return shot;
  }

  /** 手前の味方の頭が敵に重なるなら、頭越しに見えるまでカメラを上げる */
  overHeads(shot) {
    const cam = this.fitCam, v = V(), w = V();
    for (let k = 0; k < 10; k++) {
      cam.position.copy(shot.pos);
      cam.lookAt(shot.look);
      cam.updateMatrixWorld();
      let hit = false;
      for (const e of this.alive) {
        v.copy(e.home).add(V(0, this.isBig(e) ? 2.5 : 0.6, 0)).project(cam);
        for (const a of this.allies) {
          w.copy(a.home).add(V(0, 2.1, 0)).project(cam);
          if (w.z < v.z && w.y > v.y && Math.abs(w.x - v.x) < 0.16) { hit = true; break; }
        }
        if (hit) break;
      }
      if (!hit) break;
      shot.pos.y += 0.45;
    }
    return shot;
  }

  makeEnemy(key, m, pos) {
    const def = MONSTERS[key];
    return { key, def, m, name: def.name, hp: def.hp, maxHp: def.hp, alive: true, home: pos.clone() };
  }

  get alive() { return this.enemies.filter((e) => e.alive); }
  get liveAllies() { return this.allies.filter((a) => a.m.hp > 0); }
  get isBoss() { return !!this.opts.boss; }

  // ------------------------------------------------------------ カメラ
  setShot(name, arg) {
    const d = this.dir, r = this.right, c = this.center, h0 = this.center0;
    const big = !!this.bigB;
    const S = {
      intro: () => ({ pos: c.clone().addScaledVector(d, 6).addScaledVector(r, -9).add(V(0, big ? 7 : 4, 0)), look: c.clone().add(V(0, big ? 3 : 0.8, 0)), speed: 1.2 }),
      command: () => {
        const a = arg ? arg.home : h0;
        return { pos: a.clone().addScaledVector(d, big ? -5.0 : -3.9).addScaledVector(r, big ? 2.0 : 1.3).add(V(0, big ? 3.6 : 3.0, 0)), look: a.clone().lerp(c, 0.66).add(V(0, big ? 2.6 : 0.6, 0)), speed: 3 };
      },
      side: () => ({ pos: h0.clone().lerp(c, 0.5).addScaledVector(r, big ? -13 : -8.5).add(V(0, 2.6, 0)), look: h0.clone().lerp(c, 0.5).add(V(0, 1.0, 0)), speed: 4 }),
      actorFront: () => ({ pos: arg.home.clone().addScaledVector(d, 3.4).addScaledVector(r, -1.2).add(V(0, 1.6, 0)), look: arg.home.clone().add(V(0, 1.2, 0)), speed: 4 }),
      party: () => ({ pos: h0.clone().addScaledVector(d, 5.5).add(V(0, 2.4, 0)), look: h0.clone().add(V(0, 1.0, 0)), speed: 3 }),
      enemy: () => ({ pos: h0.clone().addScaledVector(d, -2.6).addScaledVector(r, 1.8).add(V(0, 1.9, 0)), look: arg.home.clone().add(V(0, big ? 3 : 0.9, 0)), speed: 4 }),
      victory: () => ({ pos: h0.clone().addScaledVector(d, 4.2).addScaledVector(r, 1.4).add(V(0, 1.7, 0)), look: h0.clone().add(V(0, 1.2, 0)), speed: 2, orbit: true }),
      wide: () => ({ pos: c.clone().lerp(h0, 0.5).addScaledVector(r, -11).add(V(0, 6, 0)), look: c.clone().lerp(h0, 0.5).add(V(0, 1, 0)), speed: 2 }),
    };
    const shot = S[name]();
    // 敵が見切れないように自動で引く
    if (name === 'command') { this.fit(shot, this.focusPoints(false, arg)); this.overHeads(shot); }
    else if (name === 'enemy') this.fit(shot, this.focusPoints(false));
    else if (name === 'intro' || name === 'side' || name === 'wide') this.fit(shot, this.focusPoints(true));
    this.shot = shot;
  }

  updateCamera(dt) {
    const s = this.shot;
    if (!s) return;
    const cam = this.g.camera;
    if (s.orbit) {
      const off = s.pos.clone().sub(s.look);
      off.applyAxisAngle(V(0, 1, 0), dt * 0.25);
      s.pos.copy(s.look).add(off);
    }
    const k = Math.min(1, dt * s.speed);
    this.camPos.lerp(s.pos, k);
    this.camLook.lerp(s.look, k);
    const gh = this.f.env.height(this.camPos.x, this.camPos.z) + 0.5;
    if (this.camPos.y < gh) this.camPos.y = gh;
    cam.position.copy(this.camPos);
    if (this.shake > 0) {
      this.shake = Math.max(0, this.shake - dt * 2.5);
      const a = this.shake * 0.35;
      cam.position.add(V(rnd(-a, a), rnd(-a, a), rnd(-a, a)));
    }
    cam.lookAt(this.camLook);
  }

  update(dt) {
    for (const a of this.allies) a.h.update(dt);
    for (const e of this.enemies) if (e.m.root.visible) e.m.update(dt);
    this.updateCamera(dt);
    if (this.arrow && this.arrowTarget) {
      const t = this.arrowTarget;
      const hgt = t.isAlly ? 2.4 : (this.isBig(t) ? 7 : 2.0 * (t.def.scale || 1));
      const p = t.home.clone().add(V(0, hgt, 0)).project(this.g.camera);
      this.arrow.style.left = ((p.x + 1) / 2) * window.innerWidth + 'px';
      this.arrow.style.top = ((1 - p.y) / 2) * window.innerHeight + 'px';
    }
  }

  popup(p, text, cls) {
    const v = p.clone().project(this.g.camera);
    this.g.ui.popup(((v.x + 1) / 2) * window.innerWidth, ((1 - v.y) / 2) * window.innerHeight, text, cls);
  }

  tween(obj, from, to, ms, ease = (t) => t * (2 - t)) {
    return new Promise((res) => {
      const t0 = performance.now();
      const step = () => {
        const k = Math.min(1, (performance.now() - t0) / ms);
        obj.copy(from).lerp(to, ease(k));
        if (k < 1) requestAnimationFrame(step); else res();
      };
      step();
    });
  }

  // ------------------------------------------------------------ メイン
  async run() {
    const ui = this.g.ui, audio = this.g.audio;
    this.setup();
    this.setShot('intro');
    this.camPos.copy(this.shot.pos).add(V(0, 6, 0)).addScaledVector(this.right, -6);
    this.camLook.copy(this.shot.look);
    audio.play(this.opts.music || (this.opts.boss || this.opts.group ? 'boss' : 'battle'), { fade: 0.1 });
    ui.swirlOut();
    this.g.hud.update();
    this.enemyWin = ui.window('', { id: 'battle-enemies' });
    this.refreshEnemyWin();
    this.log = ui.battleLog();
    if (this.opts.boss) {
      audio.sfx('roar');
      this.shake = 1.5;
      this.enemies[0].m.lunge = 1;
      setTimeout(() => (this.enemies[0].m.lunge = 0), 900);
      await this.log.add(`${this.enemies[0].name}が あらわれた！`, 900);
    } else if (this.opts.intro) {
      await this.log.add(this.opts.intro, 800);
    } else {
      const names = [...new Set(this.enemies.map((e) => e.def.name))];
      await this.log.add(this.enemies.length > 1 ? `${names[0]}たちが あらわれた！` : `${names[0]}が あらわれた！`, 700);
    }

    let result = null;
    while (!result) {
      const acts = await this.inputAll();
      if (acts === 'flee') {
        this.log.el.classList.remove('hidden');
        this.log.clear();
        await this.log.add(`${this.allies[0].name}たちは にげだした！`, 300);
        const pa = Math.max(...this.liveAllies.map((a) => derived(a.m).agi));
        const ok = Math.random() < 0.55 + (pa - Math.max(...this.alive.map((e) => e.def.agi))) * 0.02;
        if (ok) { result = await this.doFlee(); break; }
        await this.log.add('しかし まわりこまれて しまった！', 600);
      }
      // 行動順
      const order = [];
      if (acts !== 'flee') for (const [a, act] of acts) order.push({ ally: a, act, spd: derived(a.m).agi * rnd(0.6, 1.0) });
      for (const e of this.alive) {
        const times = e.def.boss && e.hp < e.maxHp * 0.5 ? 2 : 1;
        for (let k = 0; k < times; k++) order.push({ enemy: e, spd: e.def.agi * rnd(0.6, 1.0) - k * 50 });
      }
      order.sort((a, b) => b.spd - a.spd);
      for (const a of this.allies) a.defending = false;
      if (acts !== 'flee') for (const [a, act] of acts) if (act.type === 'defend') a.defending = true;
      for (const o of order) {
        if (o.ally) { if (o.ally.m.hp > 0) await this.allyAct(o.ally, o.act); }
        else if (o.enemy.alive && this.liveAllies.length) await this.enemyAct(o.enemy);
        if (!this.liveAllies.length) { result = 'lose'; break; }
        if (!this.alive.length) { result = 'win'; break; }
      }
    }
    if (result === 'win') await this.victory();
    if (result === 'lose') await this.defeat();
    this.cleanup(result);
    return result;
  }

  refreshEnemyWin() {
    const groups = {};
    for (const e of this.alive) groups[e.def.name] = (groups[e.def.name] || 0) + 1;
    this.enemyWin.innerHTML = Object.entries(groups).map(([nm, c]) => `${nm}${c > 1 ? `　${c}ひき` : ''}`).join('<br>') || '　';
  }

  async doFlee() {
    this.g.audio.sfx('flee');
    this.allies[0].h.setWeapon(false);
    const moves = this.liveAllies.map((a) => {
      a.h.speed = 6;
      a.h.root.rotation.y += Math.PI;
      const back = a.home.clone().addScaledVector(this.dir, -6);
      return this.tween(a.h.root.position, a.h.root.position.clone(), back, 600, (t) => t);
    });
    await Promise.all(moves);
    for (const a of this.allies) a.h.speed = 0;
    this.f.pos.copy(this.allies[0].h.root.position);
    this.f.facing = this.allies[0].h.root.rotation.y;
    return 'flee';
  }

  // ------------------------------------------------------------ コマンド入力（全員分。B で前の人に戻る）
  async inputAll() {
    const acts = [];
    const live = this.liveAllies;
    let i = 0;
    while (i < live.length) {
      const a = live[i];
      this.setShot('command', a);
      const act = await this.inputOne(a, i === 0);
      if (act === 'back') { if (i > 0) { acts.pop(); i--; } continue; }
      if (act.type === 'flee') return 'flee';
      acts.push([a, act]);
      i++;
    }
    this.log.el.classList.remove('hidden');
    this.g.hud.update();
    return acts;
  }

  async inputOne(a, first) {
    const ui = this.g.ui;
    for (;;) {
      this.log.el.classList.add('hidden');
      this.g.hud.update(a.m.id);
      const isWarrior = !MEMBERS[a.m.id].base.mp;
      const i = await ui.choose([
        { label: 'たたかう' }, { label: isWarrior ? 'とくぎ' : 'じゅもん' }, { label: 'どうぐ' }, { label: 'ぼうぎょ' },
        { label: 'にげる', disabled: !first || this.isBoss || !!this.opts.noFlee },
      ], { id: 'battle-cmd', cancel: !first, title: a.name, start: a.lastCmd || 0 });
      if (i < 0) return 'back';
      a.lastCmd = i;
      if (i === 0) {
        const t = await this.pickEnemy();
        if (t) return { type: 'attack', target: t };
      } else if (i === 1) {
        const list = knownSpells(a.m).filter((k) => SPELLS[k].target !== 'field');
        if (!list.length) { this.log.el.classList.remove('hidden'); await this.log.add(isWarrior ? 'まだ とくぎを おぼえていない。' : 'まだ じゅもんを おぼえていない。', 500); continue; }
        const j = await ui.choose(list.map((k) => ({
          label: SPELLS[k].name, sub: SPELLS[k].mp ? `${SPELLS[k].mp}` : '',
          disabled: a.m.mp < SPELLS[k].mp || (SPELLS[k].target === 'dead' && !this.allies.some((x) => x.m.hp <= 0)), desc: SPELLS[k].desc,
        })), { id: 'battle-sub', title: isWarrior ? 'とくぎ' : `MP ${a.m.mp}` });
        if (j < 0) continue;
        const sp = SPELLS[list[j]];
        let target = null;
        if (sp.target === 'one') { target = await this.pickEnemy(); if (!target) continue; }
        if (sp.target === 'ally') { target = await this.pickAlly(false); if (!target) continue; }
        if (sp.target === 'dead') { target = await this.pickAlly(true); if (!target) continue; }
        return { type: 'spell', key: list[j], target };
      } else if (i === 2) {
        const list = Object.entries(this.s.items).filter(([k, n]) => n > 0 && !ITEMS[k].fieldOnly);
        if (!list.length) { this.log.el.classList.remove('hidden'); await this.log.add('つかえる どうぐを もっていない。', 500); continue; }
        const j = await ui.choose(list.map(([k, n]) => ({ label: ITEMS[k].name, sub: `×${n}`, desc: ITEMS[k].desc })), { id: 'battle-sub', title: 'どうぐ' });
        if (j < 0) continue;
        const target = await this.pickAlly(false);
        if (!target) continue;
        return { type: 'item', key: list[j][0], target };
      } else if (i === 3) return { type: 'defend' };
      else if (i === 4) return { type: 'flee' };
    }
  }

  async withArrow(list, fn) {
    this.arrow = document.createElement('div');
    this.arrow.className = 'target-arrow';
    this.arrow.textContent = '▼';
    this.g.ui.root.appendChild(this.arrow);
    this.arrowTarget = list[0];
    const r = await fn();
    this.arrow.remove();
    this.arrow = null;
    return r;
  }

  async pickEnemy() {
    const al = this.alive;
    if (al.length === 1) return al[0];
    return this.withArrow(al, async () => {
      const j = await this.g.ui.choose(al.map((e) => ({ label: e.name })), { id: 'battle-sub', title: 'だれを？', onMove: (k) => { this.arrowTarget = al[k]; } });
      return j < 0 ? null : al[j];
    });
  }

  async pickAlly(dead) {
    const list = this.allies.filter((a) => (dead ? a.m.hp <= 0 : a.m.hp > 0));
    if (!list.length) return null;
    const marks = list.map((a) => ({ isAlly: true, home: a.home }));
    return this.withArrow(marks, async () => {
      const j = await this.g.ui.choose(list.map((a) => ({ label: a.name, sub: `H ${a.m.hp}` })), { id: 'battle-sub', title: 'だれに？', onMove: (k) => { this.arrowTarget = marks[k]; } });
      return j < 0 ? null : list[j];
    });
  }

  // ------------------------------------------------------------ 味方の行動
  async allyAct(a, act) {
    const audio = this.g.audio, fx = this.g.fx, m = a.m, d = derived(m);
    this.log.clear();
    if (act.type === 'defend') { await this.log.add(`${a.name}は みを まもっている。`, 450); return; }
    if (act.type === 'item') {
      const it = ITEMS[act.key];
      if (!this.s.items[act.key]) { await this.log.add(`${it.name}は もう ない！`, 400); return; }
      this.s.items[act.key]--;
      const t = act.target.m.hp > 0 ? act.target : a;
      await this.log.add(`${a.name}は ${it.name}を つかった！`, 200);
      this.setShot('actorFront', t);
      if (it.use === 'heal') await this.healFx(t, rint(...it.power));
      if (it.use === 'mp') {
        const v = Math.min(derived(t.m).maxMp - t.m.mp, it.power[0]);
        t.m.mp += v;
        audio.sfx('heal');
        fx.emit({ pos: t.home.clone().add(V(0, 1, 0)), count: 40, color: [0x88bbff, 0xffffff], speed: 1.5, up: 1.5, life: 1.2, size: 0.3, spread: 1 });
        this.g.hud.update();
        await this.log.add(`${t.name}の MPが ${v} かいふくした！`, 600);
      }
      return;
    }
    let target = act.target;
    if (target && target.alive === false) target = this.alive[0];
    if (act.type === 'attack') {
      await this.log.add(`${a.name}の こうげき！`, 150);
      await this.meleeAttack(a, target, d.atk, false);
      return;
    }
    // 呪文・特技
    const sp = SPELLS[act.key];
    if (m.mp < sp.mp) { await this.log.add('しかし MPが たりない！', 400); return; }
    m.mp -= sp.mp;
    this.g.hud.update();
    await this.log.add(sp.skill ? `${a.name}の ${sp.name}！` : `${a.name}は ${sp.name}を となえた！`, 100);
    if (!sp.skill) {
      this.setShot('actorFront', a);
      audio.sfx('spell');
      for (let k = 0; k < 3; k++) fx.emit({ pos: a.home.clone().add(V(0, 0.1, 0)), count: 30, color: [0xffe9a0, 0x9fd0ff], speed: 0.8, up: 2.5, life: 1.1, size: 0.22, spread: 1.6, flat: true });
      await a.h.play('Cast', { timeScale: 1.2 });
    }
    if (sp.target === 'ally') {
      const t = target && target.m.hp > 0 ? target : a;
      await this.healFx(t, rint(...sp.power));
      return;
    }
    if (sp.target === 'allies') {
      this.setShot('party');
      for (const t of this.liveAllies) this.healFx(t, rint(...sp.power), true);
      await sleep(400);
      await this.log.add('なかまたちの HPが かいふくした！', 600);
      return;
    }
    if (act.key === 'revive') {
      const t = target && target.m.hp <= 0 ? target : this.allies.find((x) => x.m.hp <= 0);
      if (!t) { await this.log.add('しかし なにも おこらなかった。', 400); return; }
      t.m.hp = Math.ceil(derived(t.m).maxHp / 2);
      this.uncoffin(t);
      audio.sfx('light');
      fx.emit({ pos: t.home.clone(), count: 120, color: [0xffffff, 0xfff0a0], speed: 1, up: 3, life: 1.6, size: 0.3, spread: 1.5, flicker: 18 });
      fx.flashLight(t.home.clone().add(V(0, 2, 0)), 0xfff0c0, 50, 1.2);
      this.g.hud.update();
      await this.log.add(`${t.name}が いきかえった！`, 700);
      return;
    }
    if (act.key === 'lightbreak') { await this.meleeAttack(a, target, rint(...sp.power), true); return; }
    if (sp.melee) {
      const list = sp.target === 'all' ? this.alive.slice() : [target];
      for (const t of list) {
        if (!t || !t.alive) continue;
        await this.meleeAttack(a, t, Math.round(d.atk * sp.melee), false, list.length > 1);
      }
      return;
    }
    if (act.key === 'warcry') {
      this.setShot('wide');
      audio.sfx('roar');
      this.shake = 1.2;
      a.h.play('Victory', { timeScale: 1.6 });
      fx.emit({ pos: a.home.clone().add(V(0, 1.6, 0)), count: 60, color: [0xffd0a0, 0xffffff], speed: 6, life: 0.6, size: 0.3 });
      await sleep(500);
      for (const t of this.alive.slice()) await this.damageEnemy(t, rint(...sp.power), false);
      return;
    }
    this.setShot('side');
    const targets = sp.target === 'all' ? this.alive : [target];
    await this.spellFx(act.key, a, targets);
    for (const t of targets) {
      if (!t.alive) continue;
      await this.damageEnemy(t, rint(...sp.power), false);
    }
  }

  async meleeAttack(a, target, atk, special, quick = false) {
    const audio = this.g.audio, fx = this.g.fx;
    if (!quick) this.setShot('side');
    const start = a.h.root.position.clone();
    const reach = this.isBig(target) ? 4.2 : 1.5 + (target.def.scale || 1) * 0.4 + (target.def.boss ? 1 : 0);
    const to = target.home.clone().addScaledVector(this.dir, -reach);
    to.y = this.f.env.height(to.x, to.z);
    a.h.speed = 6;
    a.h.root.rotation.y = Math.atan2(to.x - start.x, to.z - start.z);
    await this.tween(a.h.root.position, start, to, quick ? 250 : 380, (t) => t);
    a.h.speed = 0;
    a.h.root.rotation.y = Math.atan2(this.dir.x, this.dir.z);
    const anim = a.h.play('Attack', { timeScale: special ? 0.8 : 1.2 });
    audio.sfx('swing');
    await sleep(special ? 470 : 320);
    const crit = special || Math.random() < 1 / 24;
    const miss = !special && Math.random() < 1 / 30;
    const hitPos = target.home.clone().add(V(0, this.isBig(target) ? 3 : 0.8 * (target.def.scale || 1), 0));
    fx.slash(hitPos.clone().addScaledVector(this.dir, -0.3), this.dir.clone().negate(), special ? 0xffe27a : 0xcfe8ff, special ? 2.6 : 1.6);
    if (special) {
      audio.sfx('light');
      fx.flashLight(hitPos, 0xffe8a0, 60, 0.6);
      fx.emit({ pos: hitPos, count: 120, color: [0xfff3c0, 0xffd060, 0xffffff], speed: 7, life: 1.0, size: 0.4 });
      this.g.ui.flashScreen('#fff6d0', 300, 0.7);
    }
    if (miss) {
      audio.sfx('miss');
      this.popup(hitPos, 'ミス', 'miss');
      await anim;
      await this.log.add(`ミス！ ${target.name}は ひらりと みをかわした！`, 400);
    } else {
      let dmg = special ? atk : crit ? Math.round(atk * rnd(0.95, 1.05)) : Math.round((atk / 2 - target.def.def / 4) * rnd(0.85, 1.15));
      if (dmg < 1) dmg = Math.random() < 0.5 ? 1 : 0;
      if (crit && !special) { this.g.ui.flashScreen('#fff', 120, 0.6); await this.log.add('かいしんの いちげき！', 100); }
      await this.damageEnemy(target, dmg, crit);
      await anim;
    }
    a.h.speed = 6;
    a.h.root.rotation.y = Math.atan2(a.home.x - a.h.root.position.x, a.home.z - a.h.root.position.z);
    await this.tween(a.h.root.position, a.h.root.position.clone(), a.home, quick ? 250 : 380, (t) => t);
    a.h.root.rotation.y = Math.atan2(this.dir.x, this.dir.z);
    a.h.speed = 0;
  }

  async damageEnemy(t, dmg, crit) {
    const audio = this.g.audio, fx = this.g.fx;
    const hp = t.home.clone().add(V(0, this.isBig(t) ? 3.2 : 0.8 * (t.def.scale || 1), 0));
    audio.sfx(crit ? 'crit' : 'hit');
    t.m.hitFlash();
    this.shake = crit ? 1.0 : 0.35;
    fx.emit({ pos: hp, count: crit ? 50 : 22, color: [0xffffff, 0xffe6a0], speed: crit ? 7 : 4.5, life: 0.45, size: 0.2, drag: 3 });
    const knock = t.home.clone().addScaledVector(this.dir, t.def.boss ? 0.3 : 0.7);
    this.tween(t.m.root.position, t.home, knock, 90).then(() => this.tween(t.m.root.position, knock, t.home, 260));
    this.popup(hp, String(dmg), crit ? 'crit' : '');
    t.hp -= dmg;
    await this.log.add(`${t.name}に ${dmg}の ダメージ！`, 320);
    if (t.hp <= 0) await this.killEnemy(t);
  }

  async killEnemy(t) {
    const audio = this.g.audio, fx = this.g.fx;
    t.alive = false;
    this.refreshEnemyWin();
    audio.sfx('kill');
    const big = this.isBig(t);
    const p = t.home.clone().add(V(0, big ? 3 : 0.7, 0));
    fx.emit({ pos: p, count: big ? 300 : 70, color: big ? [0xffffff, 0xffe080, 0xb080ff] : [0xffffff, 0xc8b8ff, 0x99ccff], speed: big ? 9 : 3, up: 1.5, life: big ? 2.2 : 1.1, size: big ? 0.5 : 0.28, drag: 1.2, spread: big ? 4 : 0.8 });
    if (big) { this.shake = 2; this.g.ui.flashScreen('#fff', 1200, 1); fx.flashLight(p, 0xffffff, 120, 2.5); }
    const m = t.m, s0 = m.root.scale.clone(), t0 = performance.now();
    if (t.key === 'dragon') {
      // 魔竜は消えない（やみが抜けて正気に戻る）
      m.lunge = -0.8;
      await sleep(2200);
      m.lunge = 0;
      await this.log.add(`${t.name}を たおした！`, 280);
      return;
    }
    await new Promise((res) => {
      const step = () => {
        const k = Math.min(1, (performance.now() - t0) / (big ? 2200 : 650));
        m.hitFlash();
        m.flash = 1 - k * 0.5;
        m.setOpacity(1 - k);
        m.root.scale.copy(s0).multiplyScalar(1 + k * (big ? 0.15 : -0.3));
        m.root.position.y = t.home.y + k * (big ? 1.5 : 0.4);
        if (k < 1) requestAnimationFrame(step); else res();
      };
      step();
    });
    m.root.visible = false;
    await this.log.add(`${t.name}を たおした！`, 280);
  }

  async healFx(t, amount, quiet = false) {
    const fx = this.g.fx, audio = this.g.audio;
    const v = Math.min(derived(t.m).maxHp - t.m.hp, amount);
    t.m.hp += v;
    audio.sfx('heal');
    fx.emit({ pos: t.home.clone().add(V(0, 0.2, 0)), count: 70, color: [0x9dffb0, 0xffffff, 0xe0ffd0], speed: 0.6, up: 2.2, life: 1.4, size: 0.25, spread: 1.4, flicker: 20 });
    fx.flashLight(t.home.clone().add(V(0, 1.5, 0)), 0x9dffb0, 20, 1.2);
    this.popup(t.home.clone().add(V(0, 2, 0)), String(v), 'heal');
    this.g.hud.update();
    if (!quiet) await this.log.add(`${t.name}の HPが ${v} かいふくした！`, 600);
  }

  async spellFx(key, a, targets) {
    const fx = this.g.fx, audio = this.g.audio;
    const hand = a.home.clone().add(V(0, 1.4, 0)).addScaledVector(this.dir, 0.6);
    const flyTo = async (to, colors, light, size) => {
      const ball = hand.clone(), t0 = performance.now();
      await new Promise((res) => {
        const step = () => {
          const k = Math.min(1, (performance.now() - t0) / 450);
          ball.copy(hand).lerp(to, k);
          ball.y += Math.sin(k * Math.PI) * 1.2;
          fx.emit({ pos: ball, count: 6, color: colors, speed: 0.6, life: 0.4, size, grow: -0.5 });
          fx.flashLight(ball, light, 25, 0.15);
          if (k < 1) requestAnimationFrame(step); else res();
        };
        step();
      });
    };
    if (key === 'fire') {
      const t = targets[0], to = t.home.clone().add(V(0, this.isBig(t) ? 3 : 0.8, 0));
      audio.sfx('fire');
      await flyTo(to, [0xffaa33, 0xff5511, 0xffee88], 0xff8833, 0.55);
      fx.emit({ pos: to, count: 90, color: [0xffcc55, 0xff6611, 0xff3300], speed: 5, up: 2, life: 0.9, size: 0.6, grow: 0.8 });
      fx.flashLight(to, 0xff7722, 70, 0.6);
    } else if (key === 'blizzard') {
      const t = targets[0], to = t.home.clone().add(V(0, this.isBig(t) ? 3 : 0.6, 0));
      audio.sfx('storm');
      this.setShot('wide');
      const t0 = performance.now();
      await new Promise((res) => {
        const step = () => {
          const k = (performance.now() - t0) / 1100;
          for (let i = 0; i < 3; i++) {
            const a2 = k * 18 + i * 2.1;
            fx.emit({ pos: to.clone().add(V(Math.cos(a2) * 1.8, 4 - k * 3, Math.sin(a2) * 1.8)), count: 2, color: [0xe8f6ff, 0x9fd8ff, 0xffffff], speed: 1.5, dir: V(0, -6, 0), life: 0.6, size: 0.35, drag: 0.5 });
          }
          fx.flashLight(to.clone().add(V(0, 2, 0)), 0x9fd8ff, 45, 0.15);
          if (k < 1) requestAnimationFrame(step); else res();
        };
        step();
      });
      fx.emit({ pos: to, count: 100, color: [0xffffff, 0xbfe8ff], speed: 6, life: 0.8, size: 0.4 });
      this.g.ui.flashScreen('#dff4ff', 200, 0.5);
    } else if (key === 'lightning') {
      const t = targets[0], to = t.home.clone().add(V(0, this.isBig(t) ? 2 : 0.4, 0));
      this.setShot('wide');
      await sleep(250);
      audio.sfx('thunder');
      for (let k = 0; k < 3; k++) {
        fx.bolt(to.clone().add(V(rnd(-2, 2), 26, rnd(-2, 2))), to);
        this.g.ui.flashScreen('#cfe4ff', 140, 0.7);
        fx.flashLight(to.clone().add(V(0, 3, 0)), 0xbfe0ff, 120, 0.3);
        this.shake = 0.8;
        await sleep(110);
      }
      fx.emit({ pos: to, count: 80, color: [0xffffff, 0x9fd0ff], speed: 6, life: 0.6, size: 0.35 });
    } else if (key === 'storm') {
      audio.sfx('storm');
      this.setShot('wide');
      const t0 = performance.now();
      await new Promise((res) => {
        const step = () => {
          const k = (performance.now() - t0) / 1300;
          for (const t of targets) {
            for (let i = 0; i < 4; i++) {
              const a2 = k * 14 + i * 1.57, r = 1.6 - k * 0.6;
              fx.emit({ pos: t.home.clone().add(V(Math.cos(a2) * r, k * 3 + i * 0.3, Math.sin(a2) * r)), count: 2, color: [0xffaa33, 0xff4411, 0xffdd66], speed: 0.4, up: 1.2, life: 0.7, size: 0.7 });
            }
          }
          fx.flashLight(this.center.clone().add(V(0, 2, 0)), 0xff6622, 60, 0.15);
          if (k < 1) requestAnimationFrame(step); else res();
        };
        step();
      });
    }
  }

  // ------------------------------------------------------------ 敵の行動
  async enemyAct(e) {
    const audio = this.g.audio, fx = this.g.fx;
    this.log.clear();
    this.setShot('enemy', e);
    const def = e.def;
    let mode = 'attack';
    if (def.skill && Math.random() < (def.boss ? 0.45 : 0.3)) mode = def.skill;
    if (e.m.kind === 'Dragon' && mode === 'attack' && Math.random() < 0.4) mode = 'tail';
    if (def.breath && mode === 'attack' && Math.random() < 0.25) mode = def.skill;
    const target = pick(this.liveAllies);

    const hit = async (a, dmg, quiet) => {
      if (a.defending) dmg = Math.round(dmg / 2);
      dmg = Math.max(0, dmg);
      a.m.hp = Math.max(0, a.m.hp - dmg);
      audio.sfx('hurt');
      this.shake = Math.min(1.4, 0.4 + dmg / 40);
      this.g.ui.flashScreen('#ff2020', 220, Math.min(0.45, 0.1 + dmg / 120));
      const p = a.home.clone().add(V(0, 1.1, 0));
      fx.emit({ pos: p, count: 18, color: [0xffffff, 0xff8866], speed: 3.5, life: 0.4, size: 0.18 });
      this.popup(p.clone().add(V(0, 0.8, 0)), String(dmg), 'player');
      if (a.m.hp <= 0) a.h.play('Down', { hold: true });
      else a.h.play('Hurt', { timeScale: 1.1 });
      this.g.hud.update();
      if (!quiet) await this.log.add(`${a.name}は ${dmg}の ダメージを うけた！`, 420);
      if (a.m.hp <= 0) await this.log.add(`${a.name}は たおれた！`, 500);
      if (a.m.hp <= 0 && !quiet) await this.coffinize(a);
    };
    const base = (a) => Math.round((def.atk / 2 - derived(a.m).def / 4) * rnd(0.85, 1.15));
    const lunge = async (a, fn) => {
      const from = e.home.clone();
      const to = e.home.clone().lerp(a.home, def.boss ? 0.25 : 0.62);
      to.y = this.f.env.height(to.x, to.z);
      e.m.speed = 4;
      await this.tween(e.m.root.position, from, to, 260);
      e.m.lunge = 1;
      await fn();
      e.m.lunge = 0;
      await this.tween(e.m.root.position, e.m.root.position.clone(), from, 320);
      e.m.speed = 0;
    };
    const all = async (dmgOf) => {
      const hitList = this.liveAllies;
      for (const a of hitList) await hit(a, dmgOf(a), true);
      await this.log.add('なかまたちは ダメージを うけた！', 450);
      for (const a of hitList) if (a.m.hp <= 0) await this.log.add(`${a.name}は たおれた！`, 400);
      for (const a of hitList) if (a.m.hp <= 0) await this.coffinize(a);
    };

    switch (mode) {
      case 'attack':
        await this.log.add(`${e.name}の こうげき！`, 150);
        await lunge(target, async () => {
          if (Math.random() < 1 / 28) { audio.sfx('miss'); this.popup(target.home.clone().add(V(0, 1.5, 0)), 'ミス', 'miss'); await this.log.add(`${target.name}は ひらりと みをかわした！`, 400); return; }
          const b = base(target);
          await hit(target, b < 1 ? rint(0, 1) : b);
        });
        break;
      case 'strike':
        await this.log.add(`${e.name}${def.skillText}`, 150);
        await lunge(target, async () => {
          this.shake = 1.0;
          fx.emit({ pos: target.home.clone().add(V(0, 1.1, 0)), count: 30, color: [0xffffff, 0xffd0a0], speed: 4, life: 0.45, size: 0.22 });
          await hit(target, Math.max(1, Math.round(base(target) * (def.skillMul || 1.4))));
        });
        break;
      case 'allhit':
        await this.log.add(`${e.name}${def.skillText}`, 150);
        audio.sfx('swing');
        fx.emit({ pos: e.home.clone().add(V(0, 1, 0)), count: 70, color: [0xffffff, 0xd8ffa0], speed: 6, life: 0.6, size: 0.18, spread: 1.2 });
        await sleep(350);
        await all((a) => Math.max(1, Math.round(base(a) * (def.skillMul || 0.6))));
        break;
      case 'magicall': {
        await this.log.add(`${e.name}${def.skillText}`, 150);
        this.setShot('wide');
        audio.sfx(def.breath ? 'breath' : 'fire');
        const col = def.fxColor || [0xffffff, 0xa0c0ff];
        const from = e.home.clone().add(V(0, this.isBig(e) ? 4.2 : 1.4 * (def.scale || 1), 0));
        const mid = this.center0.clone().add(V(0, 1.1, 0));
        e.m.lunge = -0.6;
        const t0 = performance.now();
        await new Promise((res) => {
          const step = () => {
            const k = Math.min(1, (performance.now() - t0) / 1100);
            const dv = mid.clone().sub(from).normalize();
            fx.emit({ pos: from, count: 10, color: col, speed: 2, dir: dv.multiplyScalar(13), life: 0.9, size: 0.8, grow: 2, drag: 0.6 });
            fx.flashLight(from.clone().lerp(mid, 0.6), col[0], 60, 0.15);
            if (k < 1) requestAnimationFrame(step); else res();
          };
          step();
        });
        e.m.lunge = 0;
        for (const a of this.liveAllies) fx.emit({ pos: a.home.clone().add(V(0, 1, 0)), count: 30, color: col, speed: 3, life: 0.6, size: 0.4 });
        await all((a) => Math.max(1, Math.round(rint(...def.skillPow) * (a.defending ? 0.5 : 1) * (1 - Math.min(0.3, derived(a.m).def / 900)))));
        break;
      }
      case 'spore':
        await this.log.add(`${e.name}は あやしい ほうしを まきちらした！`, 150);
        audio.sfx('miss');
        fx.emit({ pos: e.home.clone().add(V(0, 1, 0)), count: 90, color: [0xd090ff, 0x9fff90, 0xffffff], speed: 2, dir: this.dir.clone().multiplyScalar(-5), life: 1.4, size: 0.35, drag: 0.8, spread: 2 });
        await sleep(500);
        await all((a) => Math.max(1, Math.round(base(a) * 0.55 + rint(1, 4))));
        break;
      case 'drain':
        await this.log.add(`${e.name}は きゅうけつ こうげきを しかけてきた！`, 150);
        await lunge(target, async () => {
          const dmg = Math.max(1, base(target));
          await hit(target, dmg);
          const heal = Math.min(e.maxHp - e.hp, Math.ceil(dmg / 2));
          e.hp += heal;
          fx.emit({ pos: e.home.clone().add(V(0, 1.5, 0)), count: 25, color: [0xff4466, 0xffaacc], speed: 1, up: 1, life: 0.8, size: 0.25 });
          if (heal > 0) await this.log.add(`${e.name}は HPを すいとった！`, 300);
        });
        break;
      case 'fire': {
        await this.log.add(`${e.name}は ファイアを となえた！`, 150);
        audio.sfx('fire');
        const warm = e.key === 'wisp';
        const fc = warm ? [0xffd070, 0xff6a20, 0xffffff] : [0x8fb8ff, 0x3a6aff, 0xffffff];
        const from = e.home.clone().add(V(0, 1.6, 0)), to = target.home.clone().add(V(0, 1.1, 0)), t0 = performance.now();
        await new Promise((res) => {
          const step = () => {
            const k = Math.min(1, (performance.now() - t0) / 450);
            const b = from.clone().lerp(to, k);
            fx.emit({ pos: b, count: 5, color: fc, speed: 0.6, life: 0.35, size: 0.5 });
            fx.flashLight(b, warm ? 0xff8833 : 0x6699ff, 20, 0.15);
            if (k < 1) requestAnimationFrame(step); else res();
          };
          step();
        });
        fx.emit({ pos: to, count: 50, color: fc, speed: 4, life: 0.7, size: 0.5 });
        await hit(target, rint(...(e.key === 'ghost_blue' || e.key === 'wisp_blue' ? [20, 28] : [9, 14])));
        break;
      }
      case 'smash':
        await this.log.add(`${e.name}は おおきく うでを ふりかぶった！`, 150);
        await lunge(target, async () => {
          this.shake = 1.6;
          fx.emit({ pos: target.home.clone().add(V(0, 0.2, 0)), count: 60, color: [0xb8a888, 0x8a7a66], speed: 4, up: 2, life: 1.0, size: 0.6, gravity: 6 });
          await hit(target, Math.round(base(target) * 1.5));
        });
        break;
      case 'breath': {
        await this.log.add(`${e.name}は はげしい ほのおを はいた！`, 150);
        this.setShot('wide');
        audio.sfx('breath');
        const mouth = e.home.clone().add(V(0, 4.6, 0)).addScaledVector(this.dir, -2.2);
        const mid = this.center0.clone().add(V(0, 1.1, 0));
        e.m.lunge = -0.6;
        const t0 = performance.now();
        await new Promise((res) => {
          const step = () => {
            const k = Math.min(1, (performance.now() - t0) / 1300);
            const dv = mid.clone().sub(mouth).normalize();
            fx.emit({ pos: mouth, count: 12, color: [0xffdd66, 0xff7722, 0xff3300], speed: 2, dir: dv.multiplyScalar(14), life: 0.9, size: 1.0, grow: 2.2, drag: 0.6 });
            fx.flashLight(mouth.clone().lerp(mid, 0.6), 0xff6622, 80, 0.15);
            if (k < 1) requestAnimationFrame(step); else res();
          };
          step();
        });
        e.m.lunge = 0;
        await all(() => rint(30, 44));
        break;
      }
      case 'tail':
        await this.log.add(`${e.name}は しっぽを ふりまわした！`, 150);
        audio.sfx('roar');
        this.shake = 1.2;
        await all((a) => Math.round(base(a) * 0.85));
        break;
      default: break;
    }
  }

  // ------------------------------------------------------------ 結果
  async victory() {
    const audio = this.g.audio, s = this.s;
    this.enemyWin.remove();
    const exp = this.enemies.reduce((a, e) => a + e.def.exp, 0);
    const gold = this.enemies.reduce((a, e) => a + e.def.gold, 0);
    this.setShot('victory');
    for (const a of this.liveAllies) a.h.play('Victory', { hold: true });
    if (this.opts.boss === 'dragon' || this.enemies[0].def.final) {
      audio.play('victory');
      await this.log.add(this.enemies[0].def.final ? `${this.enemies[0].name}は ひかりの なかへ きえていった……。` : `${this.enemies[0].name}は ちからつき、 ひざを ついた……。`, 1500);
      return;
    }
    audio.jingle('victory', this.g.fieldMusic());
    this.log.clear();
    await this.log.add('まものたちを やっつけた！', 400);
    await this.log.add(`それぞれ ${exp}ポイントの けいけんちを かくとく！`, 400);
    s.gold += gold;
    audio.sfx('coin');
    await this.log.add(`${gold}ゴールドを てにいれた！`, 600);
    this.g.hud.update();
    for (const a of this.liveAllies) {
      for (const u of gainExp(a.m, exp)) {
        audio.jingle('levelup', this.g.fieldMusic());
        this.g.fx.emit({ pos: a.home.clone().add(V(0, 0.2, 0)), count: 120, color: [0xffe680, 0xffffff], speed: 1, up: 3, life: 1.6, size: 0.25, spread: 1.6, flicker: 25 });
        this.g.fx.flashLight(a.home.clone().add(V(0, 2, 0)), 0xffe6a0, 40, 1.5);
        await this.log.add(`${a.name}は レベル ${u.lv}に あがった！`, 900);
        await this.log.add(`ちから+${u.d.str}　すばやさ+${u.d.agi}　さいだいHP+${u.d.maxHp}　さいだいMP+${u.d.maxMp}`, 900);
        for (const k of u.learned) await this.log.add(`${a.name}は ${SPELLS[k].name}を おぼえた！`, 700);
        this.g.hud.update();
      }
    }
    await this.g.ui.waitKey(null, { indicator: this.log.el });
  }

  async defeat() {
    this.g.audio.play('gameover', { fade: 0.2 });
    this.g.renderer.grade.uniforms.uDesat.value = 0.8;
    await this.log.add(`${this.allies[0].name}たちは ぜんめつした……。`, 1800);
    await this.g.ui.waitKey(null, { indicator: this.log.el });
  }

  cleanup(result) {
    this.log.remove();
    if (this.enemyWin) this.enemyWin.remove();
    for (const e of this.enemies) {
      if (e.m === this.f.boss || e.m === this.f.guardian) continue;
      this.g.scene.remove(e.m.root);
    }
    if (this.opts.boss && result === 'win' && this.opts.boss !== 'dragon') this.bossObj.root.visible = false;
    for (const a of this.allies) { if (a.m.hp > 0) a.h.stopOneShot(); a.h.speed = 0; }
    this.allies[0].h.setWeapon(false);
    this.g.world.veg.setExclude(null);
    this.f.setVisible(true);
    this.f.resetFollowers();
    this.g.renderer.grade.uniforms.uDesat.value = 0;
  }
}
