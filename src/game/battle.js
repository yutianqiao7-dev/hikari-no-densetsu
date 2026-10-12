import * as THREE from 'three';
import { Monster, angDiff } from '../actors/actor.js';
import { MONSTERS, SPELLS, ITEMS, encounterTable } from './data.js';
import { derived, knownSpells, gainExp } from './state.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rnd = (a, b) => a + Math.random() * (b - a);
const rint = (a, b) => Math.floor(rnd(a, b + 1));
const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);

export class Battle {
  /**
   * @param game
   * @param opts { symbol: 野外のモンスター, boss: true }
   */
  constructor(game, opts) {
    this.g = game;
    this.f = game.field;
    this.opts = opts;
    this.hero = this.f.hero;
    this.s = game.state;
    this.enemies = [];
    this.shake = 0;
    this.camPos = game.camera.position.clone();
    this.camLook = this.f.cam.target.clone();
    this.shot = null;
    this.t = 0;
    this.arrow = null;
    this.defending = false;
  }

  // ------------------------------------------------------------ 準備
  setup() {
    const f = this.f, w = this.g.world;
    const heroPos = f.pos.clone();
    let dir;
    if (this.opts.boss) {
      const bp = f.boss.root.position;
      dir = V(bp.x - heroPos.x, 0, bp.z - heroPos.z).normalize();
      heroPos.copy(bp).addScaledVector(dir, -12.5);
      heroPos.y = w.hf.height(heroPos.x, heroPos.z);
    } else if (this.opts.symbol) {
      const sp = this.opts.symbol.root.position;
      dir = V(sp.x - heroPos.x, 0, sp.z - heroPos.z);
      if (dir.lengthSq() < 0.01) dir.set(Math.sin(f.facing), 0, Math.cos(f.facing));
      dir.normalize();
    } else dir = V(Math.sin(f.facing), 0, Math.cos(f.facing));
    this.dir = dir;
    this.right = V(dir.z, 0, -dir.x);
    this.heroHome = heroPos.clone();
    f.pos.copy(heroPos);
    f.facing = Math.atan2(dir.x, dir.z);
    this.hero.root.position.copy(heroPos);
    this.hero.root.rotation.y = f.facing;
    this.hero.speed = 0;
    this.hero.setWeapon(true);

    // 敵の編成
    if (this.opts.boss) {
      const m = f.boss;
      this.enemies.push(this.makeEnemy('dragon', m, m.root.position.clone()));
    } else {
      const sym = this.opts.symbol;
      const tab = encounterTable(heroPos.x, heroPos.z, this.g.sky.night > 0.5);
      const keys = [sym.key];
      const extra = Math.random() < 0.65 ? rint(0, Math.min(2, tab.lv >= 3 ? 2 : 1)) : 0;
      for (let i = 0; i < extra; i++) keys.push(Math.random() < 0.6 ? sym.key : tab.list[rint(0, tab.list.length - 1)]);
      const n = keys.length;
      keys.forEach((k, i) => {
        const lat = (i - (n - 1) / 2) * 2.9;
        const p = heroPos.clone().addScaledVector(dir, 6.2 + Math.abs(lat) * 0.25).addScaledVector(this.right, lat);
        p.y = w.hf.height(p.x, p.z);
        const m = new Monster(w.lib, MONSTERS[k]);
        m.root.position.copy(p);
        m.root.rotation.y = Math.atan2(-dir.x, -dir.z);
        this.g.scene.add(m.root);
        this.enemies.push(this.makeEnemy(k, m, p));
      });
      f.removeMonster(sym);
    }
    // 同じ種類が複数なら A, B, C
    const count = {};
    for (const e of this.enemies) count[e.key] = (count[e.key] || 0) + 1;
    const idx = {};
    for (const e of this.enemies) {
      if (count[e.key] > 1) { idx[e.key] = (idx[e.key] || 0) + 1; e.name = e.def.name + ' ' + 'ABCD'[idx[e.key] - 1]; }
    }
    f.setVisible(false);
    if (this.opts.boss) f.boss.root.visible = true;
    this.hero.root.visible = true;
    this.center = this.enemies.reduce((a, e) => a.add(e.home), V()).multiplyScalar(1 / this.enemies.length);
  }

  makeEnemy(key, m, pos) {
    const def = MONSTERS[key];
    return { key, def, m, name: def.name, hp: def.hp, maxHp: def.hp, alive: true, home: pos.clone() };
  }

  get alive() { return this.enemies.filter((e) => e.alive); }

  // ------------------------------------------------------------ カメラ
  setShot(name, arg) {
    const h = this.heroHome, d = this.dir, r = this.right;
    const boss = !!this.opts.boss;
    const c = this.center;
    const S = {
      intro: () => ({ pos: c.clone().addScaledVector(d, 6).addScaledVector(r, -9).add(V(0, boss ? 7 : 4, 0)), look: c.clone().add(V(0, boss ? 3 : 0.8, 0)), speed: 1.2 }),
      command: () => ({ pos: h.clone().addScaledVector(d, boss ? -4.5 : -3.3).addScaledVector(r, boss ? 2.2 : 1.35).add(V(0, boss ? 2.4 : 1.75, 0)), look: h.clone().lerp(c, 0.62).add(V(0, boss ? 3.0 : 0.85, 0)), speed: 3 }),
      heroSide: () => ({ pos: h.clone().lerp(c, 0.5).addScaledVector(r, boss ? -12 : -7.5).add(V(0, 2.4, 0)), look: h.clone().lerp(c, 0.5).add(V(0, 1.0, 0)), speed: 4 }),
      heroFront: () => ({ pos: h.clone().addScaledVector(d, 3.4).addScaledVector(r, -1.2).add(V(0, 1.6, 0)), look: h.clone().add(V(0, 1.2, 0)), speed: 4 }),
      enemy: () => {
        const e = arg.home;
        return { pos: h.clone().addScaledVector(d, -2.4).addScaledVector(r, 1.8).add(V(0, 1.7, 0)), look: e.clone().add(V(0, boss ? 3 : 0.9, 0)), speed: 4 };
      },
      victory: () => ({ pos: h.clone().addScaledVector(d, 3.2).addScaledVector(r, 1.4).add(V(0, 1.5, 0)), look: h.clone().add(V(0, 1.3, 0)), speed: 2, orbit: true }),
      wide: () => ({ pos: c.clone().lerp(h, 0.5).addScaledVector(r, -10).add(V(0, 6, 0)), look: c.clone().lerp(h, 0.5).add(V(0, 1, 0)), speed: 2 }),
    };
    this.shot = S[name]();
    this.shot.name = name;
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
    const gh = this.g.world.hf.height(this.camPos.x, this.camPos.z) + 0.5;
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
    this.t += dt;
    this.hero.update(dt);
    for (const e of this.enemies) if (e.m.root.visible) e.m.update(dt);
    this.updateCamera(dt);
    if (this.arrow && this.arrowTarget) {
      const p = this.arrowTarget.home.clone().add(V(0, (this.arrowTarget.def.boss ? 7 : 2.0) * (this.arrowTarget.def.scale || 1), 0)).project(this.g.camera);
      this.arrow.style.left = ((p.x + 1) / 2) * window.innerWidth + 'px';
      this.arrow.style.top = ((1 - p.y) / 2) * window.innerHeight + 'px';
    }
  }

  screenPos(p) {
    const v = p.clone().project(this.g.camera);
    return [((v.x + 1) / 2) * window.innerWidth, ((1 - v.y) / 2) * window.innerHeight];
  }

  popup(p, text, cls) { const [x, y] = this.screenPos(p); this.g.ui.popup(x, y, text, cls); }

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
    audio.play(this.opts.boss ? 'boss' : 'battle', { fade: 0.1 });
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
    } else {
      const names = [...new Set(this.enemies.map((e) => e.def.name))];
      await this.log.add(this.enemies.length > 1 ? `${names[0]}たちが あらわれた！` : `${names[0]}が あらわれた！`, 700);
    }

    let result = null;
    while (!result) {
      this.setShot('command');
      const act = await this.playerCommand();
      if (act.type === 'flee' && !this.opts.boss) {
        this.log.clear();
        await this.log.add(`${this.s.name}は にげだした！`, 300);
        const ok = Math.random() < 0.55 + (derived(this.s).agi - Math.max(...this.alive.map((e) => e.def.agi))) * 0.02;
        if (ok) {
          audio.sfx('flee');
          this.hero.setWeapon(false);
          this.hero.speed = 6;
          const back = this.heroHome.clone().addScaledVector(this.dir, -6);
          this.hero.root.rotation.y += Math.PI;
          await this.tween(this.hero.root.position, this.hero.root.position.clone(), back, 600, (t) => t);
          this.hero.speed = 0;
          this.f.pos.copy(this.hero.root.position);
          this.f.facing = this.hero.root.rotation.y;
          result = 'flee';
          break;
        }
        await this.log.add('しかし まわりこまれて しまった！', 600);
      }
      // 行動順
      const d = derived(this.s);
      const order = [{ who: 'hero', act, spd: d.agi * rnd(0.6, 1.0) }];
      for (const e of this.alive) {
        const times = e.def.boss && e.hp < e.maxHp * 0.5 ? 2 : 1;
        for (let k = 0; k < times; k++) order.push({ who: e, spd: e.def.agi * rnd(0.6, 1.0) - k * 50 });
      }
      order.sort((a, b) => b.spd - a.spd);
      this.defending = act.type === 'defend';
      for (const o of order) {
        if (o.who === 'hero') {
          if (act.type !== 'flee') await this.heroAct(act);
        } else if (o.who.alive) {
          await this.enemyAct(o.who);
        }
        if (this.s.hp <= 0) { result = 'lose'; break; }
        if (!this.alive.length) { result = 'win'; break; }
      }
      this.defending = false;
    }

    if (result === 'win') await this.victory();
    if (result === 'lose') await this.defeat();
    this.cleanup(result);
    return result;
  }

  refreshEnemyWin() {
    const groups = {};
    for (const e of this.alive) groups[e.def.name] = (groups[e.def.name] || 0) + 1;
    this.enemyWin.innerHTML = Object.entries(groups).map(([n, c]) => `${n}${c > 1 ? `　${c}ひき` : ''}`).join('<br>') || '　';
  }

  // ------------------------------------------------------------ コマンド入力
  async playerCommand() {
    const ui = this.g.ui;
    for (;;) {
      this.log.el.classList.add('hidden');
      this.g.hud.update();
      const i = await ui.choose([
        { label: 'たたかう' }, { label: 'じゅもん' }, { label: 'どうぐ' }, { label: 'ぼうぎょ' }, { label: 'にげる', disabled: !!this.opts.boss },
      ], { id: 'battle-cmd', cancel: false, title: this.s.name, start: this._lastCmd || 0 });
      this._lastCmd = i;
      if (i === 0) {
        const t = await this.pickTarget();
        if (t) { this.log.el.classList.remove('hidden'); return { type: 'attack', target: t }; }
      } else if (i === 1) {
        const list = knownSpells(this.s).filter((k) => SPELLS[k].target !== 'field');
        if (!list.length) { this.log.el.classList.remove('hidden'); await this.log.add('まだ じゅもんを おぼえていない。', 500); continue; }
        const j = await ui.choose(list.map((k) => ({ label: SPELLS[k].name, sub: `${SPELLS[k].mp}`, disabled: this.s.mp < SPELLS[k].mp, desc: SPELLS[k].desc })),
          { id: 'battle-sub', title: 'MP ' + this.s.mp });
        if (j < 0) continue;
        const sp = SPELLS[list[j]];
        let target = null;
        if (sp.target === 'one') { target = await this.pickTarget(); if (!target) continue; }
        this.log.el.classList.remove('hidden');
        return { type: 'spell', key: list[j], target };
      } else if (i === 2) {
        const list = Object.entries(this.s.items).filter(([k, n]) => n > 0 && !ITEMS[k].fieldOnly);
        if (!list.length) { this.log.el.classList.remove('hidden'); await this.log.add('つかえる どうぐを もっていない。', 500); continue; }
        const j = await ui.choose(list.map(([k, n]) => ({ label: ITEMS[k].name, sub: `×${n}`, desc: ITEMS[k].desc })), { id: 'battle-sub', title: 'どうぐ' });
        if (j < 0) continue;
        this.log.el.classList.remove('hidden');
        return { type: 'item', key: list[j][0] };
      } else if (i === 3) {
        this.log.el.classList.remove('hidden');
        return { type: 'defend' };
      } else if (i === 4) {
        this.log.el.classList.remove('hidden');
        return { type: 'flee' };
      }
    }
  }

  async pickTarget() {
    const al = this.alive;
    if (al.length === 1) return al[0];
    this.arrow = document.createElement('div');
    this.arrow.className = 'target-arrow';
    this.arrow.textContent = '▼';
    this.g.ui.root.appendChild(this.arrow);
    this.arrowTarget = al[0];
    const j = await this.g.ui.choose(al.map((e) => ({ label: e.name })), {
      id: 'battle-sub', title: 'だれを？', onMove: (k) => { this.arrowTarget = al[k]; },
    });
    this.arrow.remove();
    this.arrow = null;
    return j < 0 ? null : al[j];
  }

  // ------------------------------------------------------------ 勇者の行動
  async heroAct(act) {
    const audio = this.g.audio, fx = this.g.fx, s = this.s, d = derived(s);
    this.log.clear();
    if (act.type === 'defend') { await this.log.add(`${s.name}は みを まもっている。`, 500); return; }
    if (act.type === 'item') {
      const it = ITEMS[act.key];
      s.items[act.key]--;
      await this.log.add(`${s.name}は ${it.name}を つかった！`, 200);
      this.setShot('heroFront');
      if (it.use === 'heal') await this.healFx(rint(...it.power));
      if (it.use === 'mp') {
        const v = Math.min(d.maxMp - s.mp, it.power[0]);
        s.mp += v;
        audio.sfx('heal');
        fx.emit({ pos: this.hero.root.position.clone().add(V(0, 1, 0)), count: 40, color: [0x88bbff, 0xffffff], speed: 1.5, up: 1.5, life: 1.2, size: 0.3, spread: 1 });
        this.g.hud.update();
        await this.log.add(`MPが ${v} かいふくした！`, 600);
      }
      return;
    }
    let target = act.target;
    if (target && !target.alive) target = this.alive[0];
    if (act.type === 'attack') {
      await this.log.add(`${s.name}の こうげき！`, 150);
      await this.meleeAttack(target, d.atk, false);
      return;
    }
    if (act.type === 'spell') {
      const sp = SPELLS[act.key];
      s.mp -= sp.mp;
      this.g.hud.update();
      await this.log.add(`${s.name}は ${sp.name}を となえた！`, 100);
      this.setShot('heroFront');
      audio.sfx('spell');
      const hp = this.hero.root.position.clone();
      for (let k = 0; k < 3; k++) fx.emit({ pos: hp.clone().add(V(0, 0.1, 0)), count: 30, color: [0xffe9a0, 0x9fd0ff], speed: 0.8, up: 2.5, life: 1.1, size: 0.22, spread: 1.6, flat: true });
      await this.hero.play('Cast', { timeScale: 1.2 });
      if (act.key === 'heal' || act.key === 'highheal') { await this.healFx(rint(...sp.power)); return; }
      if (act.key === 'lightbreak') { await this.meleeAttack(target, rint(...sp.power), true); return; }
      this.setShot('heroSide');
      const targets = sp.target === 'all' ? this.alive : [target];
      await this.spellFx(act.key, targets);
      for (const t of targets) {
        if (!t.alive) continue;
        const dmg = rint(...sp.power);
        await this.damageEnemy(t, dmg, false);
      }
    }
  }

  async meleeAttack(target, atk, special) {
    const audio = this.g.audio, fx = this.g.fx;
    this.setShot('heroSide');
    const start = this.hero.root.position.clone();
    const reach = target.def.boss ? 4.2 : 1.5 + (target.def.scale || 1) * 0.4;
    const to = target.home.clone().addScaledVector(this.dir, -reach);
    to.y = this.g.world.hf.height(to.x, to.z);
    this.hero.speed = 6;
    await this.tween(this.hero.root.position, start, to, 380, (t) => t);
    this.hero.speed = 0;
    const anim = this.hero.play('Attack', { timeScale: special ? 0.8 : 1.15 });
    audio.sfx('swing');
    await sleep(special ? 470 : 330);
    const crit = special || Math.random() < 1 / 24;
    const miss = !special && Math.random() < 1 / 30;
    const hitPos = target.home.clone().add(V(0, target.def.boss ? 3 : 0.8 * (target.def.scale || 1), 0));
    fx.slash(hitPos.clone().addScaledVector(this.dir, -0.3), this.dir.clone().negate(), special ? 0xffe27a : 0xcfe8ff, special ? 2.6 : 1.6);
    if (special) {
      audio.sfx('light');
      fx.flashLight(hitPos, 0xffe8a0, 60, 0.6);
      fx.emit({ pos: hitPos, count: 120, color: [0xfff3c0, 0xffd060, 0xffffff], speed: 7, life: 1.0, size: 0.4 });
      this.g.ui.flashScreen('#fff6d0', 300, 0.7);
    }
    let dmg;
    if (miss) {
      audio.sfx('miss');
      this.popup(hitPos, 'ミス', 'miss');
      await anim;
      await this.log.add(`ミス！ ${target.name}は ひらりと みをかわした！`, 400);
    } else {
      dmg = special ? atk : crit ? Math.round(atk * rnd(0.95, 1.05)) : Math.round((atk / 2 - target.def.def / 4) * rnd(0.85, 1.15));
      if (dmg < 1) dmg = Math.random() < 0.5 ? 1 : 0;
      if (crit && !special) { this.g.ui.flashScreen('#fff', 120, 0.6); await this.log.add('かいしんの いちげき！', 100); }
      await this.damageEnemy(target, dmg, crit);
      await anim;
    }
    this.hero.speed = 6;
    this.hero.root.rotation.y = Math.atan2(-this.dir.x, -this.dir.z);
    await this.tween(this.hero.root.position, this.hero.root.position.clone(), this.heroHome, 380, (t) => t);
    this.hero.root.rotation.y = Math.atan2(this.dir.x, this.dir.z);
    this.hero.speed = 0;
  }

  async damageEnemy(t, dmg, crit) {
    const audio = this.g.audio, fx = this.g.fx;
    const hp = t.home.clone().add(V(0, t.def.boss ? 3.2 : 0.8 * (t.def.scale || 1), 0));
    audio.sfx(crit ? 'crit' : 'hit');
    t.m.hitFlash();
    this.shake = crit ? 1.0 : 0.35;
    fx.emit({ pos: hp, count: crit ? 50 : 22, color: [0xffffff, 0xffe6a0], speed: crit ? 7 : 4.5, life: 0.45, size: 0.2, drag: 3 });
    // のけぞり
    const knock = t.home.clone().addScaledVector(this.dir, t.def.boss ? 0.3 : 0.7);
    this.tween(t.m.root.position, t.home, knock, 90).then(() => this.tween(t.m.root.position, knock, t.home, 260));
    this.popup(hp, String(dmg), crit ? 'crit' : '');
    t.hp -= dmg;
    await this.log.add(`${t.name}に ${dmg}の ダメージ！`, 350);
    if (t.hp <= 0) await this.killEnemy(t);
  }

  async killEnemy(t) {
    const audio = this.g.audio, fx = this.g.fx;
    t.alive = false;
    this.refreshEnemyWin();
    audio.sfx('kill');
    const p = t.home.clone().add(V(0, t.def.boss ? 3 : 0.7, 0));
    const big = t.def.boss;
    fx.emit({ pos: p, count: big ? 300 : 70, color: big ? [0xffffff, 0xffe080, 0xb080ff] : [0xffffff, 0xc8b8ff, 0x99ccff], speed: big ? 9 : 3, up: 1.5, life: big ? 2.2 : 1.1, size: big ? 0.5 : 0.28, drag: 1.2, spread: big ? 4 : 0.8 });
    if (big) { this.shake = 2; this.g.ui.flashScreen('#fff', 1200, 1); fx.flashLight(p, 0xffffff, 120, 2.5); }
    const m = t.m;
    const s0 = m.root.scale.clone();
    const t0 = performance.now();
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
    await this.log.add(`${t.name}を たおした！`, 300);
  }

  async healFx(amount) {
    const s = this.s, d = derived(s), fx = this.g.fx, audio = this.g.audio;
    const v = Math.min(d.maxHp - s.hp, amount);
    s.hp += v;
    audio.sfx('heal');
    const p = this.hero.root.position.clone();
    fx.emit({ pos: p.clone().add(V(0, 0.2, 0)), count: 80, color: [0x9dffb0, 0xffffff, 0xe0ffd0], speed: 0.6, up: 2.2, life: 1.4, size: 0.25, spread: 1.4, flicker: 20 });
    fx.flashLight(p.clone().add(V(0, 1.5, 0)), 0x9dffb0, 20, 1.2);
    this.popup(p.clone().add(V(0, 2, 0)), String(v), 'heal');
    this.g.hud.update();
    await this.log.add(`${s.name}の HPが ${v} かいふくした！`, 600);
  }

  async spellFx(key, targets) {
    const fx = this.g.fx, audio = this.g.audio;
    const hand = this.hero.root.position.clone().add(V(0, 1.4, 0)).addScaledVector(this.dir, 0.6);
    if (key === 'fire') {
      const t = targets[0];
      const to = t.home.clone().add(V(0, t.def.boss ? 3 : 0.8, 0));
      audio.sfx('fire');
      const ball = hand.clone();
      const t0 = performance.now();
      await new Promise((res) => {
        const step = () => {
          const k = Math.min(1, (performance.now() - t0) / 450);
          ball.copy(hand).lerp(to, k);
          ball.y += Math.sin(k * Math.PI) * 1.2;
          fx.emit({ pos: ball, count: 6, color: [0xffaa33, 0xff5511, 0xffee88], speed: 0.6, life: 0.4, size: 0.55, grow: -0.5 });
          fx.flashLight(ball, 0xff8833, 25, 0.15);
          if (k < 1) requestAnimationFrame(step); else res();
        };
        step();
      });
      fx.emit({ pos: to, count: 90, color: [0xffcc55, 0xff6611, 0xff3300], speed: 5, up: 2, life: 0.9, size: 0.6, grow: 0.8 });
      fx.flashLight(to, 0xff7722, 70, 0.6);
    } else if (key === 'lightning') {
      const t = targets[0];
      const to = t.home.clone().add(V(0, t.def.boss ? 2 : 0.4, 0));
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
              const a = k * 14 + i * 1.57;
              const r = 1.6 - k * 0.6;
              fx.emit({ pos: t.home.clone().add(V(Math.cos(a) * r, k * 3 + i * 0.3, Math.sin(a) * r)), count: 2, color: [0xffaa33, 0xff4411, 0xffdd66], speed: 0.4, up: 1.2, life: 0.7, size: 0.7 });
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
    const s = this.s, d = derived(s), audio = this.g.audio, fx = this.g.fx;
    this.log.clear();
    this.setShot('enemy', e);
    const def = e.def;
    let mode = 'attack';
    if (def.skill && Math.random() < (def.boss ? 0.45 : 0.3)) mode = def.skill;
    if (def.boss && mode === 'attack' && Math.random() < 0.4) mode = 'tail';
    const heroP = this.hero.root.position.clone().add(V(0, 1.1, 0));

    const hitHero = async (dmg, label) => {
      if (this.defending) dmg = Math.max(0, Math.round(dmg / 2));
      dmg = Math.max(0, dmg);
      s.hp = Math.max(0, s.hp - dmg);
      audio.sfx('hurt');
      this.shake = Math.min(1.4, 0.4 + dmg / 40);
      this.g.ui.flashScreen('#ff2020', 220, Math.min(0.5, 0.12 + dmg / 120));
      this.hero.play('Hurt', { timeScale: 1.1 });
      this.popup(heroP.clone().add(V(0, 0.8, 0)), String(dmg), 'player');
      fx.emit({ pos: heroP, count: 18, color: [0xffffff, 0xff8866], speed: 3.5, life: 0.4, size: 0.18 });
      this.g.hud.update();
      await this.log.add(label || `${s.name}は ${dmg}の ダメージを うけた！`, 450);
    };

    const lunge = async (fn) => {
      const from = e.home.clone();
      const to = e.home.clone().lerp(this.heroHome, def.boss ? 0.25 : 0.62);
      to.y = this.g.world.hf.height(to.x, to.z);
      e.m.speed = 4;
      await this.tween(e.m.root.position, from, to, 260);
      e.m.lunge = 1;
      await fn();
      e.m.lunge = 0;
      await this.tween(e.m.root.position, e.m.root.position.clone(), from, 320);
      e.m.speed = 0;
    };

    const base = Math.round((def.atk / 2 - d.def / 4) * rnd(0.85, 1.15));
    switch (mode) {
      case 'attack':
        await this.log.add(`${e.name}の こうげき！`, 150);
        await lunge(async () => {
          if (Math.random() < 1 / 28) { audio.sfx('miss'); this.popup(heroP, 'ミス', 'miss'); await this.log.add(`${s.name}は ひらりと みをかわした！`, 400); return; }
          await hitHero(base < 1 ? rint(0, 1) : base);
        });
        break;
      case 'spore':
        await this.log.add(`${e.name}は あやしい ほうしを まきちらした！`, 150);
        audio.sfx('miss');
        fx.emit({ pos: e.home.clone().add(V(0, 1, 0)), count: 70, color: [0xd090ff, 0x9fff90, 0xffffff], speed: 2, dir: this.dir.clone().multiplyScalar(-5), life: 1.4, size: 0.35, drag: 0.8 });
        await sleep(500);
        await hitHero(Math.max(1, Math.round(base * 0.8 + rint(2, 5))));
        break;
      case 'drain':
        await this.log.add(`${e.name}は きゅうけつ こうげきを しかけてきた！`, 150);
        await lunge(async () => {
          const dmg = Math.max(1, base);
          await hitHero(dmg);
          const heal = Math.min(e.maxHp - e.hp, Math.ceil(dmg / 2));
          e.hp += heal;
          fx.emit({ pos: e.home.clone().add(V(0, 1.5, 0)), count: 25, color: [0xff4466, 0xffaacc], speed: 1, up: 1, life: 0.8, size: 0.25 });
          if (heal > 0) await this.log.add(`${e.name}は HPを すいとった！`, 300);
        });
        break;
      case 'fire': {
        await this.log.add(`${e.name}は ファイアを となえた！`, 150);
        audio.sfx('fire');
        const from = e.home.clone().add(V(0, 1.6, 0));
        const t0 = performance.now();
        await new Promise((res) => {
          const step = () => {
            const k = Math.min(1, (performance.now() - t0) / 450);
            const b = from.clone().lerp(heroP, k);
            fx.emit({ pos: b, count: 5, color: [0x8fb8ff, 0x3a6aff, 0xffffff], speed: 0.6, life: 0.35, size: 0.5 });
            fx.flashLight(b, 0x6699ff, 20, 0.15);
            if (k < 1) requestAnimationFrame(step); else res();
          };
          step();
        });
        fx.emit({ pos: heroP, count: 50, color: [0x8fb8ff, 0x3a6aff, 0xffffff], speed: 4, life: 0.7, size: 0.5 });
        await hitHero(rint(...(e.key === 'ghost_blue' ? [20, 28] : [9, 14])));
        break;
      }
      case 'smash':
        await this.log.add(`${e.name}は おおきく うでを ふりかぶった！`, 150);
        await lunge(async () => {
          this.shake = 1.6;
          fx.emit({ pos: this.heroHome.clone().add(V(0, 0.2, 0)), count: 60, color: [0xb8a888, 0x8a7a66], speed: 4, up: 2, life: 1.0, size: 0.6, gravity: 6 });
          await hitHero(Math.round(base * 1.5));
        });
        break;
      case 'breath': {
        await this.log.add(`${e.name}は はげしい ほのおを はいた！`, 150);
        this.setShot('wide');
        audio.sfx('breath');
        const mouth = e.home.clone().add(V(0, 4.6, 0)).addScaledVector(this.dir, -2.2);
        e.m.lunge = -0.6;
        const t0 = performance.now();
        await new Promise((res) => {
          const step = () => {
            const k = Math.min(1, (performance.now() - t0) / 1300);
            const dirv = heroP.clone().sub(mouth).normalize();
            fx.emit({ pos: mouth, count: 10, color: [0xffdd66, 0xff7722, 0xff3300], speed: 1.5, dir: dirv.multiplyScalar(14), life: 0.9, size: 0.9, grow: 1.8, drag: 0.6 });
            fx.flashLight(mouth.clone().lerp(heroP, 0.6), 0xff6622, 80, 0.15);
            if (k < 1) requestAnimationFrame(step); else res();
          };
          step();
        });
        e.m.lunge = 0;
        await hitHero(rint(34, 48));
        break;
      }
      case 'tail':
        await this.log.add(`${e.name}は しっぽを ふりまわした！`, 150);
        audio.sfx('roar');
        this.shake = 1.2;
        await hitHero(Math.round(base * 1.25));
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
    this.hero.play('Victory', { hold: true });
    if (this.opts.boss) {
      audio.play('victory');
      await this.log.add(`${this.enemies[0].name}は ひかりの なかへ きえていった……。`, 1500);
      return;
    }
    audio.jingle('victory', this.g.fieldMusic());
    this.log.clear();
    await this.log.add('まものたちを やっつけた！', 400);
    await this.log.add(`${exp}ポイントの けいけんちを かくとく！`, 400);
    s.gold += gold;
    audio.sfx('coin');
    await this.log.add(`${gold}ゴールドを てにいれた！`, 600);
    this.g.hud.update();
    const ups = gainExp(s, exp);
    for (const u of ups) {
      audio.jingle('levelup', this.g.fieldMusic());
      this.g.fx.emit({ pos: this.hero.root.position.clone().add(V(0, 0.2, 0)), count: 120, color: [0xffe680, 0xffffff], speed: 1, up: 3, life: 1.6, size: 0.25, spread: 1.6, flicker: 25 });
      this.g.fx.flashLight(this.hero.root.position.clone().add(V(0, 2, 0)), 0xffe6a0, 40, 1.5);
      await this.log.add(`${s.name}は レベル ${u.lv}に あがった！`, 900);
      await this.log.add(`ちから+${u.d.str}　すばやさ+${u.d.agi}　さいだいHP+${u.d.maxHp}　さいだいMP+${u.d.maxMp}`, 900);
      for (const k of u.learned) await this.log.add(`${s.name}は ${SPELLS[k].name}を おぼえた！`, 700);
      this.g.hud.update();
    }
    await this.g.ui.waitKey();
  }

  async defeat() {
    const audio = this.g.audio;
    this.hero.play('Down', { hold: true });
    audio.play('gameover', { fade: 0.2 });
    this.g.renderer.grade.uniforms.uDesat.value = 0.8;
    await this.log.add(`${this.s.name}は ちからつきた……。`, 1800);
    await this.g.ui.waitKey();
  }

  cleanup(result) {
    this.log.remove();
    if (this.enemyWin) this.enemyWin.remove();
    for (const e of this.enemies) {
      if (e.def.boss) continue;
      this.g.scene.remove(e.m.root);
    }
    if (this.opts.boss && result === 'win') this.f.boss.root.visible = false;
    this.hero.stopOneShot();
    this.hero.setWeapon(false);
    this.f.setVisible(true);
    this.g.renderer.grade.uniforms.uDesat.value = 0;
    void angDiff;
  }
}
