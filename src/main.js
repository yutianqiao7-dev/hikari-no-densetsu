import './style.css';
import * as THREE from 'three';
import { Renderer, QUALITY, loadQualityKey } from './core/renderer.js';
import { SkySystem } from './world/sky.js';
import { World } from './world/world.js';
import { UI } from './ui/ui.js';
import { HUD } from './ui/hud.js';
import { Input } from './input.js';
import { Audio } from './audio.js';
import { FX } from './fx.js';
import { Field } from './game/field.js';
import { Battle } from './game/battle.js';
import { TALK, expForLevel, CHESTS, ITEMS, EQUIP } from './game/data.js';
import { newState, derived, save, load, hasSave, gainExp } from './game/state.js';
import { fieldMenu, inn, shop } from './game/menu.js';
import { AREAS } from './world/world.js';
import { CUT } from './world/surfaces.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

class Game {
  constructor() {
    this.qKey = loadQualityKey();
    this.q = QUALITY[this.qKey] || QUALITY.ultra;
    this.canvas = document.getElementById('c');
    this.uiRoot = document.getElementById('ui');
    this.renderer = new Renderer(this.canvas, this.q);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, this.q.far + 300);
    this.audio = new Audio();
    this.ui = new UI(this.uiRoot, this.audio);
    this.input = new Input(this.canvas, this.uiRoot);
    this.input.onKey = (k, soft) => this.onKey(k, soft);
    this.fx = new FX(this.scene);
    this.mode = 'loading';
    this.t = 0;
    this.state = null;
    this.renderer.onResize = () => this.resize();
    this.resize();
  }

  resize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.fov = w < h ? 64 : 48;
    this.camera.updateProjectionMatrix();
    this.fx.setViewport(h * this.renderer.r.getPixelRatio());
    if (this.world && this.world.amb) this.world.amb.setViewport(h * this.renderer.r.getPixelRatio());
  }

  // ------------------------------------------------------------ 起動
  async boot() {
    const ld = document.createElement('div');
    ld.id = 'loading';
    ld.innerHTML = '<div class="t">ひかりの伝説</div><div class="bar"><i></i></div><div class="s">せかいを よみこんでいます…</div>';
    this.uiRoot.appendChild(ld);
    const bar = ld.querySelector('i');
    this.sky = new SkySystem(this.scene, this.renderer.r, this.q);
    this.world = new World(this.scene, this.renderer.r, this.sky, this.q, this.camera, this.fx);
    await this.world.load((p) => { bar.style.width = `${Math.round(p * 100)}%`; });
    ld.querySelector('.s').textContent = 'シェーダーを じゅんびしています…';
    this.resize();
    this.hud = new HUD(this);
    this.hud.buildBaseMap(this.world);
    this.hud.setVisible(false);
    this.field = new Field(this);
    const st = this.world.marker('Start');
    this.field.place(st.pos, st.rot);
    this.sky.update(0, this.field.pos, this.camera);
    await sleep(30);
    try { this.renderer.r.compile(this.scene, this.camera); } catch { /* noop */ }
    this.clock = new THREE.Timer();
    this.loop();
    await sleep(200);
    ld.style.transition = 'opacity .8s';
    ld.style.opacity = 0;
    setTimeout(() => ld.remove(), 800);
    const dev = new URLSearchParams(location.search);
    if (dev.has('dev')) {
      this.state = newState('ユウト');
      this.state.flags.metKing = true;
      if (dev.has('lv')) { gainExp(this.state, expForLevel(+dev.get('lv'))); const d = derived(this.state); this.state.hp = d.maxHp; this.state.mp = d.maxMp; }
      if (dev.has('t')) this.sky.time = +dev.get('t');
      if (dev.has('x')) this.field.place(new THREE.Vector3(+dev.get('x'), 0, +dev.get('z')), +(dev.get('r') || 0));
      this.sky.envTimer = 999;
      this.enterField();
      if (dev.has('battle')) {
        setTimeout(() => {
          const f = this.field;
          for (let i = 0; i < 40 && !f.mons.length; i++) { f.spawnT = 0; f.updateMonsters(0.016, this.t); }
          const m = f.mons[0];
              m.root.position.copy(f.pos).add(new THREE.Vector3(Math.sin(f.facing) * 3, 0, Math.cos(f.facing) * 3));
          this.startBattle(m);
        }, 800);
      }
      if (dev.has('orb')) { this.state.flags.orb = this.state.flags.guardian = true; }
      if (dev.has('area')) setTimeout(() => this.enterInterior(dev.get('area'), dev.get('at') || 'S', true), 300);
      if (dev.has('boss')) setTimeout(async () => { await this.enterInterior('tower3', 'D', true); this.startBattle(null, 'dragon'); }, 300);
      return;
    }
    this.title();
  }

  loop() {
    requestAnimationFrame(() => this.loop());
    this.clock.update();
    const dt = Math.min(this.clock.getDelta(), 0.05);
    this.t += dt;
    const f = this.field;
    if (this.mode === 'title') {
      const a = this.t * 0.05;
      this.camera.position.set(-40 + Math.sin(a) * 105, 42 + Math.sin(this.t * 0.11) * 6, 60 + Math.cos(a) * 105);
      this.camera.lookAt(-40, 14, 60);
      f.hero.update(dt);
      for (const n of f.npcs) f.updateNpc(n, dt);
    } else if (this.mode === 'field') {
      const busy = this.ui.busy;
      const mv = this.input.poll(dt, busy);
      f.update(dt, this.t, busy ? { x: 0, y: 0, len: 0 } : mv, this.input.cam);
      if (this.state) this.state.playTime += dt;
    } else if (this.mode === 'battle-trans') {
      f.hero.speed = 0;
      f.hero.update(dt);
      for (const m of f.mons) m.update(dt);
    } else if (this.mode === 'battle' && this.battle) {
      this.input.poll(dt, true);
      this.battle.update(dt);
    } else if (this.mode === 'cutscene') {
      this.input.poll(dt, true);
      f.hero.update(dt);
      for (const n of f.npcs) f.updateNpc(n, dt);
    }
    const focus = this.mode === 'title' ? new THREE.Vector3(-40, 7, 60) : f.pos;
    this.sky.update(dt, focus, this.camera);
    // 時間帯の色調（夜は青く・彩度を落とす、夕方は暖色）
    const gu = this.renderer.grade.uniforms, sk = this.sky;
    gu.uSaturation.value = 1.12 - sk.night * 0.45 + sk.dusk * 0.05;
    gu.uVignette.value = 0.32;
    gu.uTint.value.set(1 - sk.night * 0.22 + sk.dusk * 0.06, 1 - sk.night * 0.1, 1 + sk.night * 0.12 - sk.dusk * 0.08);
    if (this.world.interiors.current) this.applyInteriorLighting();
    CUT.uCutOn.value = this.world.interiors.current ? 1 : 0;
    CUT.uCutCam.value.copy(this.camera.position);
    CUT.uCutTarget.value.copy(f.pos).y += 1.0;
    this.world.update(dt, this.t, this.camera.position, f.pos);
    this.fx.update(dt);
    this.ambient(dt);
    if (this.mode === 'field' || this.mode === 'cutscene') this.hud.tick(f, this.sky);
    this.renderer.render(this.scene, this.camera, this.t);
  }

  /** 夜のホタル・塔のまわりの魔力など */
  ambient(dt) {
    if (this.mode !== 'field' || !this.field.inField) return;
    const p = this.field.pos;
    // 洞窟の入口のたいまつ
    for (const k of ['Torch_Cave-1', 'Torch_Cave1']) {
      const m = this.world.marker(k);
      if (m && m.pos.distanceToSquared(p) < 60 * 60) this.fx.emit({ pos: m.pos, count: 1, color: [0xffcc55, 0xff7722], speed: 0.25, up: 1.5, life: 0.5, size: 0.4, grow: -0.6, spread: 0.25, flat: true });
    }
    this._amb = (this._amb || 0) - dt;
    if (this._amb > 0) return;
    this._amb = 0.12;
    if (this.sky.night > 0.6 && Math.random() < 0.7) {
      const a = Math.random() * Math.PI * 2, r = 3 + Math.random() * 14;
      const x = p.x + Math.cos(a) * r, z = p.z + Math.sin(a) * r;
      const h = this.world.hf.height(x, z);
      if (h > 1.5) this.fx.emit({ pos: new THREE.Vector3(x, h + 0.4 + Math.random() * 1.5, z), count: 1, color: [0xc8ff70, 0xffef80], speed: 0.4, life: 3.5, size: 0.16, drag: 0.2, flicker: 6 });
    }
    if (this.field.area === 'tower' && !this.state.flags.cleared) {
      const b = this.world.marker('Boss').pos;
      this.fx.emit({ pos: b.clone().add(new THREE.Vector3(0, 0.5, -10)), count: 4, color: [0xb070ff, 0xe0b0ff], speed: 1, up: 3, life: 2.5, size: 0.3, spread: 22, flat: true, drag: 0.4 });
    }
  }

  // ------------------------------------------------------------ 入力
  onKey(k) {
    this.audio.unlock();
    if (this.mode === 'title' && this.titleKey) { this.titleKey(k); return; }
    if (this.ui.busy) { this.ui.key(k); return; }
    if (this.mode !== 'field') return;
    if (k === 'confirm') this.interact();
    else if (k === 'menu' || k === 'cancel') this.openMenu();
  }

  async openMenu() {
    this.audio.sfx('confirm');
    await fieldMenu(this);
    this.hud.update();
  }

  // ------------------------------------------------------------ タイトル
  title() {
    this.mode = 'title';
    const t = document.createElement('div');
    t.id = 'title';
    t.innerHTML = `<div class="logo">ひかりの伝説</div><div class="sub">〜 Legend of Light 〜</div>
      <div class="press">${this.input.isTouch ? 'タップして はじめる' : 'クリック / Enter で はじめる'}</div>
      <div class="copy">オリジナル作品 ・ フィールドは Blender で制作</div>`;
    this.uiRoot.appendChild(t);
    let started = false;
    const go = async () => {
      if (started) return;
      started = true;
      this.audio.unlock();
      this.audio.play('title');
      t.querySelector('.press').remove();
      this.titleKey = null;
      const items = [];
      if (hasSave()) items.push({ label: 'ぼうけんを つづける', v: 'cont' });
      items.push({ label: 'あたらしく はじめる', v: 'new' });
      const i = await this.ui.choose(items, { cancel: false, id: 'title-menu' });
      const v = items[i].v;
      t.style.transition = 'opacity 1s';
      t.style.opacity = 0;
      setTimeout(() => t.remove(), 1000);
      if (v === 'cont') this.continueGame(); else this.newGame();
    };
    t.addEventListener('pointerup', go);
    this.titleKey = (k) => { if (k === 'confirm') go(); };
    const menuEl = () => document.getElementById('title-menu');
    const obs = new MutationObserver(() => { const m = menuEl(); if (m) { m.style.cssText = 'left:50%;top:68%;transform:translateX(-50%);min-width:11em;z-index:41'; obs.disconnect(); } });
    obs.observe(this.uiRoot, { childList: true });
  }

  async newGame() {
    const name = await this.ui.askName('ユウト');
    this.state = newState(name);
    this.mode = 'cutscene';
    await this.ui.fadeTo(1, 900);
    this.audio.play('field_night');
    const st = this.world.marker('Start');
    this.field.place(st.pos, st.rot);
    this.sky.time = 0.31;
    this.sky.envTimer = 999;
    await this.ui.say([
      'むかし この せかいは ひかりの せいれいに まもられていた。',
      'しかし あるとき、 きたの やまに 魔竜ヴァルザードが あらわれ、 せかいは すこしずつ やみに のみこまれはじめた……。',
      `そして いま、 ひとりの わかもの ${name}が 王に よばれ、 アルセリア城へと やってきた——。`,
    ], { speed: 22 });
    this.enterField();
    await this.ui.fadeTo(0, 1400);
    await this.ui.say([`まずは 城の おくに いる 王さまに あいに いこう。`,
      this.input.isTouch ? '（ひだりがわを ドラッグで いどう、 みぎがわを ドラッグで カメラ、 A で はなす、 MENU で メニュー）'
        : '（WASD/矢印で いどう、 マウスドラッグで カメラ、 Enter/Z で はなす、 Esc/M で メニュー）']);
  }

  continueGame() {
    const s = load();
    this.state = { ...newState(s.name), ...s };
    if (s.time != null) { this.sky.time = s.time; this.sky.envTimer = 999; }
    if (s.area && this.world.interiors.floors[s.area]) {
      this.enterField();
      this.enterInterior(s.area, s.pos, true);
      return;
    }
    if (s.pos) this.field.place(new THREE.Vector3(s.pos.x, 0, s.pos.z), s.pos.rot);
    this.enterField();
  }

  enterField() {
    this.mode = 'field';
    this.input.allowTouch(true);
    if (this.world.seal) this.world.seal.visible = !this.state.flags.sealBroken;
    this.hud.setVisible(true);
    this.hud.update();
    this.field.area = undefined;
    this.updateMusic(true);
  }

  snapshot() {
    const s = this.state;
    s.pos = { x: this.field.pos.x, z: this.field.pos.z, rot: this.field.facing };
    s.time = this.sky.time;
    s.area = this.field.inField ? null : this.field.env.id;
    return s;
  }

  fieldMusic() {
    if (!this.field.inField) return this.field.env.style === 'cave' ? 'cave' : 'tower';
    const a = this.field.area;
    if (a && AREAS[a].music) return AREAS[a].music;
    return this.sky.night > 0.55 ? 'field_night' : 'field';
  }

  updateMusic(force) {
    if (this.mode !== 'field' && !force) return;
    this.audio.play(this.fieldMusic());
  }

  addItem(k, n) { this.state.items[k] = (this.state.items[k] || 0) + n; }

  // ------------------------------------------------------------ 会話
  async interact() {
    const it = this.field.findInteract();
    if (!it) return;
    this.audio.sfx('confirm');
    if (it.kind === 'boss') { await this.bossEvent(); return; }
    if (it.kind === 'chest') { await this.openChest(it.obj); return; }
    if (it.kind === 'orb') { await this.orbEvent(); return; }
    if (it.kind === 'guardian') { await this.guardianEvent(); return; }
    if (it.kind === 'sign') { await this.ui.say(TALK[it.id](this)); return; }
    const n = it.obj;
    n.talking = true;
    n.h.play('Talk', { loop: true, fade: 0.3 });
    try {
      if (it.id === 'Innkeeper') await inn(this);
      else if (it.id === 'Merchant') await shop(this);
      else {
        const lines = TALK[it.id] ? TALK[it.id](this) : [{ text: '……。' }];
        await this.ui.say(lines, { onAction: async (a) => { if (a === 'save') save(this.snapshot()); } });
      }
    } finally {
      n.talking = false;
      n.h.stopOneShot(0.4);
      this.hud.update();
    }
    // 王さまに会ったら少し休ませる（DQ 風）
    if (it.id === 'King') {
      const d = derived(this.state);
      if (this.state.hp < d.maxHp || this.state.mp < d.maxMp) {
        this.state.hp = d.maxHp;
        this.state.mp = d.maxMp;
        this.hud.update();
      }
    }
  }

  // ------------------------------------------------------------ 戦闘
  async startBattle(symbol, boss = null) {
    if (this.mode !== 'field') return;
    this.mode = 'battle-trans';
    this.audio.sfx('encounter');
    this.audio.stop(0.2);
    this.field.hint.classList.add('hidden');
    this.renderer.grade.uniforms.uBlur.value = 1;
    await this.ui.swirlIn();
    this.renderer.grade.uniforms.uBlur.value = 0;
    this.battle = new Battle(this, { symbol, boss });
    this.mode = 'battle';
    this.hud.mapWrap.style.display = this.hud.clock.style.display = 'none';
    const result = await this.battle.run();
    this.battle = null;
    this.hud.mapWrap.style.display = this.hud.clock.style.display = '';
    await this.afterBattle(result, boss);
  }

  async afterBattle(result, boss) {
    if (result === 'lose') {
      await this.ui.fadeTo(1, 1200);
      if (!this.field.inField) this.leaveInterior();
      const s = this.state, d = derived(s);
      s.hp = d.maxHp; s.mp = d.maxMp;
      s.gold = Math.floor(s.gold / 2);
      const k = this.world.marker('King');
      const p = k.pos.clone().add(new THREE.Vector3(Math.sin(k.rot) * 3.2, 0, Math.cos(k.rot) * 3.2));
      this.field.place(p, k.rot + Math.PI);
      this.field.clearMonsters();
      this.mode = 'field';
      this.hud.update();
      this.updateMusic(true);
      await this.ui.fadeTo(0, 1200);
      await this.ui.say([
        { who: '王さま', text: `ゆうしゃ ${s.name}よ。 たおれて しまうとは……。` },
        { who: '王さま', text: 'しかし そなたの たびは まだ おわっては おらぬ。 もういちど たちあがるのじゃ。' },
        { text: '（もっていた ゴールドが はんぶんに なった）' },
      ]);
      return;
    }
    if (result === 'win' && boss === 'dragon') { await this.ending(); return; }
    if (result === 'win' && boss === 'guardian') {
      this.state.flags.guardian = true;
      this.mode = 'field';
      this.field.snapCamera();
      this.updateMusic(true);
      this.hud.update();
      await this.ui.say(['がんせきの番人は くずれおちた……。', 'おくの さいだんで なにかが ひかっている。']);
      return;
    }
    this.mode = 'field';
    if (result === 'flee') this.field.afterFlee();
    this.field.snapCamera();
    this.field.area = this.field.area || null;
    this.updateMusic(true);
    this.hud.update();
  }

  async bossEvent() {
    if (this.mode !== 'field') return;
    this.mode = 'cutscene';
    this.audio.play('boss', { fade: 1.5 });
    this.field.boss.lunge = 0.8;
    await this.ui.say([
      { who: '魔竜ヴァルザード', text: 'ほう…… ちいさき ひかりが ここまで きたか。' },
      { who: '魔竜ヴァルザード', text: 'この せかいは まもなく わが やみに しずむ。 おまえの ひかりも ここで ついえるのだ！' },
    ]);
    this.field.boss.lunge = 0;
    this.mode = 'field';
    await this.startBattle(null, 'dragon');
  }

  // ------------------------------------------------------------ ダンジョン
  /** フィールドの出入口（洞窟・塔の扉）に近づいた */
  async onDoor(id) {
    if (this.mode !== 'field' || this.ui.busy) return;
    if (id === 'cave') { await this.enterInterior('cave1', 'S'); return; }
    if (id === 'tower') {
      const fl = this.state.flags;
      if (!fl.orb) {
        this.mode = 'cutscene';
        this.audio.sfx('door');
        await this.ui.say(['やみの ふういんが とびらを とざしている……。', 'ふしぎな ちからで おしもどされた！']);
        const ex = this.world.marker('TowerExit');
        this.field.place(ex.pos, ex.rot);
        this.mode = 'field';
        return;
      }
      if (!fl.sealBroken) {
        this.mode = 'cutscene';
        const sp = this.world.seal.getWorldPosition(new THREE.Vector3());
        await this.ui.say(`${this.state.name}は ひかりのオーブを かかげた！`);
        this.audio.sfx('light');
        for (let k = 0; k < 4; k++) {
          this.fx.emit({ pos: sp, count: 80, color: [0xfff0a0, 0xffffff, 0xc080ff], speed: 6, life: 1.2, size: 0.4, spread: 2 });
          this.fx.flashLight(sp, 0xfff0c0, 80, 0.5);
          await sleep(250);
        }
        this.ui.flashScreen('#fff', 900, 1);
        this.world.seal.visible = false;
        fl.sealBroken = true;
        await this.ui.say('やみの ふういんが きえさった！');
        this.mode = 'field';
      }
      await this.enterInterior('tower1', 'S');
    }
  }

  /** ダンジョン内の出口・階段 */
  async onTrigger(c) {
    if (this.mode !== 'field') return;
    const id = this.field.env.id;
    const links = {
      'cave1:D': ['cave2', 'U'], 'cave2:U': ['cave1', 'D'],
      'tower1:U': ['tower2', 'D'], 'tower2:D': ['tower1', 'U'],
      'tower2:U': ['tower3', 'D'], 'tower3:D': ['tower2', 'U'],
    };
    if (c === 'S') { await this.exitToField(id.startsWith('cave') ? 'CaveExit' : 'TowerExit'); return; }
    const to = links[`${id}:${c}`];
    if (to) await this.enterInterior(to[0], to[1]);
  }

  /** ダンジョンのフロアに入る（at: 'S' | 'U' | 'D' または保存位置） */
  async enterInterior(id, at, instant = false) {
    const floor = this.world.interiors.floors[id];
    if (!floor) return;
    this.mode = 'cutscene';
    this.field.hint.classList.add('hidden');
    if (!instant) { this.audio.sfx(at === 'S' ? 'door' : 'step'); await this.ui.fadeTo(1, 450); }
    this.world.setFieldVisible(false);
    this.world.interiors.enter(id);
    this.field.setEnv(floor);
    // 開けた宝箱・取ったオーブ
    const fl = this.state.flags;
    for (const c of floor.chests) if (c.lid) c.lid.rotation.x = fl.chests && fl.chests[c.id] ? -1.9 : 0;
    if (floor.orb) floor.orb.visible = !fl.orb;
    let pos, rot;
    if (typeof at === 'object' && at) { pos = new THREE.Vector3(at.x, 0, at.z); rot = at.rot || 0; floor.trigger(pos.x, pos.z); }
    else { const a = floor.arrival(at); pos = a.pos; rot = a.rot; }
    this.field.place(pos, rot);
    this.field.cam.pitch = Math.max(this.field.cam.pitch, 0.98);
    this.field.cam.dist = Math.min(this.field.cam.dist, 10);
    this.field.snapCamera();
    this.hud.setMapEnv(floor);
    this.mode = 'field';
    this.updateMusic(true);
    if (!instant) await this.ui.fadeTo(0, 450);
    this.ui.showBanner(floor.name);
  }

  leaveInterior() {
    this.world.interiors.leave();
    this.world.setFieldVisible(true);
    this.field.setEnv(this.world.fieldEnv);
    this.hud.setMapEnv(null);
    this.sky.sun.castShadow = true;
    this.scene.background = null;
    this.field.area = undefined;
  }

  async exitToField(markerName) {
    this.mode = 'cutscene';
    this.audio.sfx('door');
    await this.ui.fadeTo(1, 450);
    this.leaveInterior();
    const m = this.world.marker(markerName);
    this.field.place(m.pos, m.rot);
    this.field.cam.pitch = 0.32;
    this.field.snapCamera();
    this.sky.envTimer = 999;
    this.mode = 'field';
    this.updateMusic(true);
    await this.ui.fadeTo(0, 450);
  }

  /** ダンジョン内の明るさ：空・太陽を消し、暗い霧とかがり火で照らす */
  applyInteriorLighting() {
    const cave = this.field.env.style === 'cave';
    const sky = this.sky;
    if (!this._black) this._black = new THREE.Color(0, 0, 0);
    this.scene.background = this._black;
    this.scene.fog.color.setRGB(cave ? 0.012 : 0.02, cave ? 0.011 : 0.012, cave ? 0.01 : 0.03);
    this.scene.fog.density = cave ? 0.034 : 0.026;
    sky.sun.intensity = 0;
    sky.sun.castShadow = false;
    sky.hemi.color.setRGB(cave ? 0.35 : 0.4, cave ? 0.38 : 0.3, cave ? 0.5 : 0.6);
    sky.hemi.groundColor.setRGB(0.06, 0.05, 0.05);
    sky.hemi.intensity = cave ? 0.75 : 0.85;
    this.scene.environmentIntensity = 0.12;
    this.renderer.r.toneMappingExposure = 0.85;
    const gu = this.renderer.grade.uniforms;
    gu.uSaturation.value = 1.05;
    gu.uTint.value.set(cave ? 1.04 : 1.02, cave ? 1.0 : 0.96, cave ? 0.95 : 1.06);
    gu.uVignette.value = 0.55;
  }

  async openChest(c) {
    const fl = this.state.flags;
    fl.chests = fl.chests || {};
    if (fl.chests[c.id]) return;
    this.mode = 'cutscene';
    fl.chests[c.id] = true;
    this.audio.sfx('door');
    if (c.lid) {
      const t0 = performance.now();
      await new Promise((res) => {
        const step = () => {
          const k = Math.min(1, (performance.now() - t0) / 450);
          c.lid.rotation.x = -1.9 * (1 - Math.pow(1 - k, 3));
          if (k < 1) requestAnimationFrame(step); else res();
        };
        step();
      });
    }
    this.fx.emit({ pos: c.pos.clone().add(new THREE.Vector3(0, 0.8, 0)), count: 40, color: [0xffe680, 0xffffff], speed: 1.2, up: 2, life: 1.0, size: 0.22, flicker: 20 });
    const got = CHESTS[c.id] || { item: 'herb', n: 1 };
    const s = this.state;
    let text;
    if (got.gold) { s.gold += got.gold; text = `${got.gold}ゴールドを てにいれた！`; this.audio.sfx('coin'); }
    else if (got.equip) { s.bag.push(got.equip); text = `${EQUIP[got.equip].name}を てにいれた！`; this.audio.sfx('item'); }
    else { this.addItem(got.item, got.n); text = `${ITEMS[got.item].name}を ${got.n}こ てにいれた！`; this.audio.sfx('item'); }
    await this.ui.say([`${s.name}は たからばこを あけた！`, text].concat(got.equip ? ['（メニューの「そうび」で そうび できます）'] : []));
    this.hud.update();
    this.mode = 'field';
  }

  async guardianEvent() {
    if (this.mode !== 'field') return;
    this.mode = 'cutscene';
    this.audio.sfx('roar');
    this.field.guardian.lunge = 1;
    await this.ui.say([
      { who: 'がんせきの番人', text: '……ひかりを もとめる ものよ。' },
      { who: 'がんせきの番人', text: 'オーブに ふさわしき ちからか、 この いわの こぶしで ためさせてもらう！' },
    ]);
    this.mode = 'field';
    await this.startBattle(null, 'guardian');
  }

  async orbEvent() {
    const fl = this.state.flags;
    if (!fl.guardian) { await this.guardianEvent(); return; }
    this.mode = 'cutscene';
    const floor = this.field.env;
    const p = floor.orb.getWorldPosition(new THREE.Vector3());
    this.fx.emit({ pos: p, count: 120, color: [0xfff0a0, 0xffffff, 0xffd060], speed: 3, up: 1, life: 1.6, size: 0.3, flicker: 15 });
    this.fx.flashLight(p, 0xfff0c0, 60, 1.5);
    floor.orb.visible = false;
    fl.orb = true;
    await this.audio.jingle('levelup', this.fieldMusic());
    await this.ui.say([`${this.state.name}は ひかりのオーブを てにいれた！`, 'あたたかな ひかりが こころを みたしていく……。', 'これで まおうの塔の ふういんを とけるはずだ。']);
    this.mode = 'field';
  }

  async warpToCastle() {
    this.mode = 'cutscene';
    this.audio.sfx('spell');
    await this.ui.fadeTo(1, 700);
    if (!this.field.inField) this.leaveInterior();
    const st = this.world.marker('Start');
    this.field.place(st.pos, st.rot);
    this.field.clearMonsters();
    this.updateMusic(true);
    await sleep(300);
    this.mode = 'field';
    this.field.area = undefined;
    await this.ui.fadeTo(0, 700);
  }

  async ending() {
    const ui = this.ui, s = this.state;
    this.mode = 'cutscene';
    s.flags.cleared = true;
    await ui.fadeTo(1, 2000);
    if (!this.field.inField) this.leaveInterior();
    this.field.clearMonsters();
    const k = this.world.marker('King');
    const p = k.pos.clone().add(new THREE.Vector3(Math.sin(k.rot) * 3.2, 0, Math.cos(k.rot) * 3.2));
    this.field.place(p, k.rot + Math.PI);
    this.sky.time = 0.42;
    this.sky.envTimer = 999;
    this.audio.play('ending');
    await sleep(600);
    await ui.fadeTo(0, 2000);
    await ui.say([
      { who: '王さま', text: `おお ${s.name}！ よくぞ もどった！` },
      { who: '王さま', text: 'まおうの塔を おおっていた やみは きえ、 せかいに ふたたび ひかりが さしこんだ。' },
      { who: '王さま', text: 'そなたこそ まことの ゆうしゃ。 この国の ほこりじゃ。 ほんとうに ありがとう。' },
    ]);
    const end = document.createElement('div');
    end.id = 'ending';
    end.innerHTML = `<div class="roll">
      <h1>ひかりの伝説</h1>
      <h2>ゆうしゃ</h2>${s.name}
      <h2>フィールド・モデル</h2>Blender（Python スクリプトで生成）
      <h2>キャラクター</h2>メタボール造形・スキニング・アニメーション
      <h2>グラフィックス</h2>Three.js / WebGL
      <h2>おんがく・こうかおん</h2>オリジナル（WebAudio シンセサイザー）
      <h2>プレイじかん</h2>${Math.floor(s.playTime / 3600)}じかん ${Math.floor((s.playTime % 3600) / 60)}ふん
      <h2>レベル</h2>${s.lv}
      <br><br><br><h1>おわり</h1>
      <div style="font-size:16px">ありがとう ございました</div></div>`;
    this.uiRoot.appendChild(end);
    this.hud.setVisible(false);
    await sleep(43000);
    end.style.transition = 'opacity 2s';
    end.style.opacity = 0;
    await sleep(2000);
    end.remove();
    save(this.snapshot());
    this.hud.setVisible(true);
    this.mode = 'field';
    this.field.area = undefined;
    await ui.say('（ぼうけんを きろくしました。 ひきつづき せかいを たんさく できます）');
  }
}

const game = new Game();
window.__game = game;
game.boot().catch((e) => {
  console.error(e);
  const d = document.createElement('div');
  d.style.cssText = 'position:fixed;inset:0;display:flex;align-items:center;justify-content:center;color:#fff;background:#000;padding:2em;white-space:pre-wrap';
  d.textContent = 'よみこみに しっぱいしました\n' + (e && e.stack || e);
  document.body.appendChild(d);
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden && game.state && game.mode === 'field') save(game.snapshot());
});
