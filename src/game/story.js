import * as THREE from 'three';
import { Humanoid, Monster } from '../actors/actor.js';
import { MONSTERS, MEMBERS } from './data.js';
import { addMember } from './state.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);

/**
 * ストーリーの強制イベント。
 *  第1章 ミナトの村の広場でミリアが魔物に襲われている → 共闘 → 仲間に
 *  第2章 ほこらの洞窟の前で騎士ガルドが苦戦 → 加勢 → 仲間に
 *  第3章 がんせきの番人を倒すと、結晶に囚われた神官セレナが目覚める → 仲間に
 *  第4章 まおうの塔に入ると魔竜の声、2F で闇のしもべの待ち伏せ
 */
export class Story {
  constructor(game) {
    this.g = game;
    this.running = false;
    this.staged = [];
    this.crystal = null;
  }

  get f() { return this.g.field; }
  get flags() { return this.g.state.flags; }

  // ------------------------------------------------------------ 演出の道具
  /** カメラを指定位置へ（ms かけて移動） */
  cam(pos, look, speed = 2.5) { this.g.cine = { pos: pos.clone(), look: look.clone(), speed }; }

  /** キャラクターを歩かせる（到着で解決） */
  walk(h, to, speed = 2.2) {
    return new Promise((res) => {
      const fn = (dt) => {
        const p = h.root.position;
        const d = V(to.x - p.x, 0, to.z - p.z);
        const dist = d.length();
        if (dist < 0.08) {
          h.speed = 0;
          this.g.tickers.delete(fn);
          res();
          return;
        }
        d.normalize();
        const step = Math.min(dist, speed * dt);
        p.x += d.x * step;
        p.z += d.z * step;
        p.y = this.f.env.height(p.x, p.z);
        h.root.rotation.y = Math.atan2(d.x, d.z);
        h.speed = speed;
      };
      this.g.tickers.add(fn);
    });
  }

  face(h, target) { h.root.rotation.y = Math.atan2(target.x - h.root.position.x, target.z - h.root.position.z); }

  /** 一時的に置くキャラクター（アニメーションも更新） */
  stageHumanoid(h, pos, rot) {
    h.root.position.copy(pos);
    h.root.position.y = this.f.env.height(pos.x, pos.z);
    h.root.rotation.y = rot;
    h.root.visible = true;
    const fn = (dt) => h.update(dt);
    this.g.tickers.add(fn);
    this.staged.push({ obj: h, fn });
    return h;
  }

  stageMonster(key, pos, lookAt) {
    const m = new Monster(this.g.world.lib, MONSTERS[key]);
    m.root.position.copy(pos);
    m.root.position.y = this.f.env.height(pos.x, pos.z);
    m.root.rotation.y = Math.atan2(lookAt.x - pos.x, lookAt.z - pos.z);
    this.g.scene.add(m.root);
    const fn = (dt) => m.update(dt);
    this.g.tickers.add(fn);
    this.staged.push({ obj: m, fn, monster: true });
    return m;
  }

  unstage(obj) {
    const i = this.staged.findIndex((s) => s.obj === obj);
    if (i < 0) return;
    const s = this.staged[i];
    this.g.tickers.delete(s.fn);
    if (s.monster || s.temp) this.g.scene.remove(s.obj.root);
    this.staged.splice(i, 1);
  }

  unstageAll() { for (const s of this.staged.slice()) this.unstage(s.obj); }

  say(lines) { return this.g.ui.say(lines); }

  async join(id) {
    const m = addMember(this.g.state, id);
    if (!m) return;
    this.g.hud.update();
    this.f.resetFollowers();
    await this.g.audio.jingle('levelup', this.g.fieldMusic());
    await this.say(`${MEMBERS[id].name}が なかまに くわわった！`);
  }

  async begin() {
    this.running = true;
    this.g.mode = 'cutscene';
    this.f.hint.classList.add('hidden');
    this.f.clearMonsters();
  }

  end() {
    this.running = false;
    this.g.cine = null;
    this.unstageAll();
    this.f.resetFollowers();
    this.f.snapCamera();
    if (this.g.mode === 'cutscene') this.g.mode = 'field';
    this.g.updateMusic(true);
  }

  /** 強制戦闘（イベントの途中） */
  async battle(group, intro) {
    this.g.cine = null;
    this.g.mode = 'field';
    const r = await this.g.startBattle(null, null, { group, noFlee: true, intro });
    this.g.mode = 'cutscene';
    return r;
  }

  // ------------------------------------------------------------ 毎フレームの発生チェック
  check() {
    if (this.running || this.g.mode !== 'field' || this.g.ui.busy || !this.g.state) return;
    const f = this.f, fl = this.flags;
    if (f.inField) {
      if (!fl.ev_village && f.area === 'village') { this.villageEvent(); return; }
      const cave = this.g.world.marker('CaveEntrance');
      if (!fl.ev_gald && cave && f.pos.distanceTo(cave.pos) < 26) { this.galdEvent(); return; }
    } else {
      const env = f.env;
      if (env.id === 'tower1' && !fl.ev_tower) { this.towerVoice(); return; }
      if (env.id === 'tower2' && !fl.ev_ambush) {
        const u = env.spots.U && env.spots.U[0];
        if (u && Math.hypot(f.pos.x - u[0], f.pos.z - u[1]) < 10) { this.ambush(); return; }
      }
    }
  }

  /** 洞窟 B2 の結晶（中にセレナ） */
  onEnterFloor(env) {
    if (this.crystal) { this.g.scene.remove(this.crystal); this.crystal = null; }
    if (this.crystalTick) { this.g.tickers.delete(this.crystalTick); this.crystalTick = null; }
    const sh = this.f.followers.serena;
    if (sh && !this.g.state.party.some((m) => m.id === 'serena')) sh.root.visible = false;
    if (env.id !== 'cave2' || this.flags.ev_serena) return;
    const o = env.spots.O && env.spots.O[0];
    if (!o || !sh) return;
    const p = V(o[0] + 4.2, 0, o[1]);
    sh.root.position.copy(p);
    sh.root.rotation.y = -Math.PI / 2;
    sh.root.visible = true;
    sh.play('Cast', { hold: true, fade: 0.01, timeScale: 0.0001 });
    const geo = new THREE.IcosahedronGeometry(1.25, 1);
    geo.scale(0.85, 1.6, 0.85);
    const mat = new THREE.MeshPhysicalMaterial({
      color: 0x9fd8ff, transparent: true, opacity: 0.38, roughness: 0.05, metalness: 0, clearcoat: 1,
      emissive: 0x2a6aa0, emissiveIntensity: 0.6, flatShading: true, depthWrite: false,
    });
    const c = new THREE.Mesh(geo, mat);
    c.position.copy(p).add(V(0, 1.15, 0));
    c.renderOrder = 3;
    this.g.scene.add(c);
    this.crystal = c;
    this.crystalPos = p;
    this.crystalTick = (dt) => { sh.update(dt); sh.root.visible = true; c.rotation.y += dt * 0.15; };
    this.g.tickers.add(this.crystalTick);
  }

  // ------------------------------------------------------------ 第1章：港の村の魔法使い
  async villageEvent() {
    const g = this.g, f = this.f;
    await this.begin();
    this.flags.ev_village = true;
    // 広場の井戸（中央）がカメラの邪魔にならないよう、東側の開けた所で起こる。P は「前＝東」の座標系
    const E = V(153, 0, 110);
    const P = (x, y, z) => { const v = E.clone().add(V(-z, 0, x)); v.y = f.env.height(v.x, v.z) + y; return v; };
    const milia = this.stageHumanoid(f.followers.milia, P(0, 0, -2.5), Math.PI / 2);
    const mons = [
      this.stageMonster('purun', P(-2.8, 0, -5.6), milia.root.position),
      this.stageMonster('purun_red', P(2.8, 0, -5.4), milia.root.position),
      this.stageMonster('purun', P(0, 0, -6.6), milia.root.position),
    ];
    this.face(milia, mons[2].root.position);
    g.audio.play('battle', { fade: 0.3 });
    this.cam(P(9, 6, 6), P(0, 1, -3), 2.5);
    await this.say([{ text: '（むらの ひろばの ほうから ひめいが きこえる！）' }]);
    await this.say([{ who: '？？？', text: 'こないで！ こないでったら！' }]);
    milia.play('Cast', { timeScale: 1.3 });
    await sleep(500);
    const tgt = mons[0].root.position.clone().add(V(0, 0.8, 0));
    g.audio.sfx('fire');
    for (let k = 0; k < 10; k++) { g.fx.emit({ pos: milia.root.position.clone().add(V(0, 1.4, 0)).lerp(tgt, k / 10), count: 4, color: [0xffaa33, 0xff5511], speed: 0.5, life: 0.4, size: 0.5 }); await sleep(30); }
    g.fx.emit({ pos: tgt, count: 60, color: [0xffcc55, 0xff6611], speed: 4, life: 0.7, size: 0.5 });
    mons[0].hitFlash();
    await this.say([{ who: '？？？', text: 'ファイア！ ……うそ、 ぜんぜん きいてない！？' }]);
    // 勇者がかけつける
    this.cam(P(-7, 5, 9), P(0, 1, -1), 2);
    await this.walk(f.hero, P(0.2, 0, 0.6), 5.5);
    this.face(f.hero, mons[2].root.position);
    f.pos.copy(f.hero.root.position);
    f.facing = f.hero.root.rotation.y;
    this.face(milia, f.hero.root.position);
    await this.say([
      { who: '？？？', text: 'あなた、 たびの ひと？ おねがい、 いっしょに たたかって！' },
    ]);
    this.face(milia, mons[2].root.position);
    for (const m of mons) this.unstage(m);
    this.unstage(milia);
    addMember(g.state, 'milia');
    g.hud.update();
    const r = await this.battle(['purun', 'purun_red', 'purun'], 'まものの むれが おそいかかってきた！');
    if (r !== 'win') { this.end(); return; }
    // 長老がかけよる
    const mi = f.followers.milia;
    this.stageHumanoid(mi, f.pos.clone().add(V(1.4, 0, 0)), Math.PI);
    const elder = new Humanoid(g.world.lib, 'Elder');
    g.scene.add(elder.root);
    this.stageHumanoid(elder, P(-9, 0, 6), -Math.PI / 2);
    this.staged[this.staged.length - 1].temp = true;
    this.cam(f.pos.clone().add(V(4, 4, 7)), f.pos.clone().add(V(-1, 1, 0)), 2);
    await this.walk(elder, f.pos.clone().add(V(-1.4, 0, 1.6)), 1.6);
    this.face(elder, mi.root.position);
    this.face(mi, elder.root.position);
    await this.say([
      { who: '長老', text: 'ミリア！ ぶじだったか……！' },
      { who: 'ミリア', text: 'おじいちゃん！ この人が たすけてくれたの。' },
    ]);
    this.face(elder, f.hero.root.position);
    this.face(f.hero, elder.root.position);
    await this.say([
      { who: '長老', text: 'そなたが 王の つかいの ゆうしゃどのか。 まごを すくってくださり かたじけない。' },
      { who: '長老', text: 'まおうの塔の とびらは やみの ふういんで とざされておる。' },
      { who: '長老', text: 'にしの いわやまの ふもと「ほこらの洞窟」の おくに ねむる「ひかりのオーブ」が あれば ふういんを やぶれるはずじゃ。' },
      { who: 'ミリア', text: 'わたしも いく！ まほうなら まかせて！ ……さっきは ちょっと しっぱい したけど。' },
      { who: '長老', text: '……やれやれ。 いいだしたら きかぬ 子じゃ。 ゆうしゃどの、 ミリアを たのみましたぞ。' },
    ]);
    await g.audio.jingle('levelup', g.fieldMusic());
    await this.say('ミリアが なかまに くわわった！');
    this.end();
  }

  // ------------------------------------------------------------ 第2章：傷ついた騎士
  async galdEvent() {
    const g = this.g, f = this.f;
    await this.begin();
    this.flags.ev_gald = true;
    const cave = g.world.marker('CaveEntrance').pos;
    const spot = cave.clone().add(V(0, 0, 11));
    spot.y = f.env.height(spot.x, spot.z);
    const gald = this.stageHumanoid(f.followers.gald, spot.clone(), Math.PI);
    const mons = [
      this.stageMonster('golem', spot.clone().add(V(-1.6, 0, -4.6)), spot),
      this.stageMonster('bat', spot.clone().add(V(2.4, 0, -3.8)), spot),
    ];
    g.audio.play('battle', { fade: 0.3 });
    this.cam(spot.clone().add(V(8, 5, 4)), spot.clone().add(V(0, 1.2, -2)), 2.5);
    gald.play('Hurt', { timeScale: 0.8 });
    await this.say([{ who: '？？？', text: 'ぐっ……！ これしきの きずで……！' }]);
    this.cam(spot.clone().add(V(-6, 4.5, 9)), spot.clone().add(V(0, 1, 0)), 2);
    const fol = f.partyFollowers();
    await this.walk(f.hero, spot.clone().add(V(-1.6, 0, 1.2)), 5.5);
    fol.forEach(({ h }, i) => { this.walk(h, spot.clone().add(V(-3.2 - i * 1.4, 0, 2.2)), 5.5); });
    this.face(f.hero, mons[0].root.position);
    f.pos.copy(f.hero.root.position);
    f.facing = f.hero.root.rotation.y;
    this.face(gald, f.hero.root.position);
    const lines = [{ who: '？？？', text: 'なんだ、 おまえたちは……？ ……いや、 ありがたい。 手を かしてくれ！' }];
    await this.say(lines);
    for (const m of mons) this.unstage(m);
    this.unstage(gald);
    addMember(g.state, 'gald');
    g.hud.update();
    const r = await this.battle(['golem', 'bat'], 'いわゴーレムが たちふさがった！');
    if (r !== 'win') { this.end(); return; }
    const ga = f.followers.gald;
    this.stageHumanoid(ga, f.pos.clone().add(V(1.6, 0, -0.4)), 0);
    this.face(ga, f.hero.root.position);
    this.face(f.hero, ga.root.position);
    this.cam(f.pos.clone().add(V(0.5, 3.5, 6.5)), f.pos.clone().add(V(0.8, 1.2, 0)), 2);
    const talk = [
      { who: 'ガルド', text: 'たすかったぜ。 おれは ガルド。 もとは 王国の 騎士だった おとこだ。' },
      { who: 'ガルド', text: 'この 洞窟の おくの「がんせきの番人」に ひとりで いどんで…… この ざまよ。' },
      { who: 'ガルド', text: 'おまえたちも ひかりのオーブを さがしているのか？ なら おれも つれていけ。 こんどこそ あの いわの かたまりを くだいてやる！' },
    ];
    if (g.state.party.some((m) => m.id === 'milia')) {
      talk.push({ who: 'ミリア', text: 'おじさん、 けが してるんだから むりしちゃ だめだよ？' });
      talk.push({ who: 'ガルド', text: 'お、 おじさん……。 おれは まだ 28だぞ……。' });
    }
    await this.say(talk);
    await g.audio.jingle('levelup', g.fieldMusic());
    await this.say('ガルドが なかまに くわわった！');
    this.end();
  }

  // ------------------------------------------------------------ 第3章：囚われの神官（番人を倒したあと）
  async serenaEvent() {
    const g = this.g, f = this.f;
    if (this.flags.ev_serena || !this.crystal) return;
    await this.begin();
    this.flags.ev_serena = true;
    const p = this.crystalPos.clone();
    const se = f.followers.serena;
    this.cam(p.clone().add(V(-5, 3.2, 5)), p.clone().add(V(0, 1.2, 0)), 2);
    await sleep(600);
    await this.say(['ふるえる ような おとが ひびく……。', 'がんせきの番人が たおれ、 そばの すいしょうに ひびが はいっていく！']);
    g.audio.sfx('light');
    for (let k = 0; k < 4; k++) {
      g.fx.emit({ pos: p.clone().add(V(0, 1.2, 0)), count: 70, color: [0xcfefff, 0xffffff, 0x9fd8ff], speed: 5, life: 1.0, size: 0.3, spread: 1.5 });
      g.fx.flashLight(p.clone().add(V(0, 1.5, 0)), 0xbfe8ff, 60, 0.4);
      await sleep(260);
    }
    g.ui.flashScreen('#fff', 800, 1);
    g.scene.remove(this.crystal);
    this.crystal = null;
    this.g.tickers.delete(this.crystalTick);
    this.crystalTick = null;
    this.stageHumanoid(se, se.root.position.clone(), se.root.rotation.y);
    se.stopOneShot(0.3);
    se.play('Hurt', { timeScale: 0.6 });
    await sleep(800);
    this.face(se, f.hero.root.position);
    await this.say([
      { who: '？？？', text: '……ここは……？ わたしは…… たすかったのですね。' },
      { who: 'セレナ', text: 'わたしは ひかりの神殿の 神官、 セレナと もうします。' },
      { who: 'セレナ', text: '塔の ふういんを しらべていて、 魔竜の しもべに とらえられ…… ずっと この すいしょうの なかに。' },
      { who: 'セレナ', text: 'ひかりのオーブは 塔の ふういんを とく かぎ。 そして 魔竜の やみを はらうには、 ひかりの いのりも ひつようです。' },
      { who: 'セレナ', text: 'どうか わたしも つれていってください。 みなさんの きずは わたしが いやします。' },
    ]);
    if (g.state.party.some((m) => m.id === 'gald')) await this.say([{ who: 'ガルド', text: 'かいふく役は ありがたい。 よろしくたのむぜ、 セレナ。' }]);
    addMember(g.state, 'serena');
    g.hud.update();
    await g.audio.jingle('levelup', g.fieldMusic());
    await this.say('セレナが なかまに くわわった！');
    this.end();
  }

  // ------------------------------------------------------------ 第4章：まおうの塔
  async towerVoice() {
    const g = this.g;
    await this.begin();
    this.flags.ev_tower = true;
    g.audio.sfx('roar');
    for (let k = 0; k < 8; k++) { g.ui.flashScreen('#400060', 200, 0.35); await sleep(120); }
    await this.say([
      { who: '？？？', text: '……よくぞ ここまで きた、 ちいさき ひかりたちよ。' },
      { who: '魔竜ヴァルザード', text: 'わしは さいじょうかいで まっている。 その ひかりごと やきつくしてくれよう……！' },
    ]);
    const ids = g.state.party.map((m) => m.id);
    const lines = [];
    if (ids.includes('gald')) lines.push({ who: 'ガルド', text: '上等だ！ まちくたびれてるのは こっちの ほうだぜ！' });
    if (ids.includes('milia')) lines.push({ who: 'ミリア', text: 'こ、 こわくなんか ないもん！ ……ほんとだよ？' });
    if (ids.includes('serena')) lines.push({ who: 'セレナ', text: 'みなさん、 ひかりを しんじて。 わたしたちは きっと かてます。' });
    if (lines.length) await this.say(lines);
    this.end();
  }

  async ambush() {
    await this.begin();
    this.flags.ev_ambush = true;
    this.g.audio.sfx('encounter');
    await this.say([{ text: 'くらやみの なかから いくつもの かげが あらわれた！' }, { who: 'やみの しもべ', text: 'まりゅうさまの もとへは いかせぬ……！' }]);
    await this.battle(['ghost_blue', 'golem', 'ghost_blue'], 'やみの しもべたちが まちぶせていた！');
    this.end();
  }

  /** 最終決戦の前の掛け合い */
  async beforeDragon() {
    const ids = this.g.state.party.map((m) => m.id);
    const lines = [];
    if (ids.includes('serena')) lines.push({ who: 'セレナ', text: 'ひかりよ…… わたしたちに ちからを！' });
    if (ids.includes('gald')) lines.push({ who: 'ガルド', text: 'いくぜ、 みんな！ ここで おわらせる！' });
    if (ids.includes('milia')) lines.push({ who: 'ミリア', text: 'おじいちゃん、 みてて。 わたし まけないから！' });
    if (lines.length) await this.say(lines);
  }


  // ================================================================ 第二部：竜とめぐる五つの島
  /** 魔竜を倒した直後：やみが抜けて正気に戻ったヴァルザードが語る */
  async dragonAwakens() {
    const g = this.g, f = this.f, d = f.boss;
    await this.begin();
    d.root.visible = true;
    d.lunge = 0;
    d.flash = 0;
    const p = d.root.position.clone();
    this.cam(p.clone().add(V(-10, 5, 12)), p.clone().add(V(0, 4, 0)), 1.2);
    g.audio.play('field_night', { fade: 2 });
    await sleep(800);
    for (let k = 0; k < 6; k++) {
      g.fx.emit({ pos: p.clone().add(V(0, 3 + k * 0.4, 0)), count: 40, color: [0x301050, 0x8040ff, 0x000000], speed: 2, up: 3, life: 1.6, size: 0.8, spread: 2.5, drag: 0.6 });
      await sleep(180);
    }
    g.ui.flashScreen('#ffffff', 900, 0.8);
    g.audio.sfx('light');
    await this.say([{ text: 'まりゅうの からだから くろい きりが ぬけていく……。' }]);
    this.cam(p.clone().add(V(-5, 3.5, 9)), p.clone().add(V(0, 4.6, -1)), 1.5);
    await this.say([
      { who: 'ヴァルザード', text: '……ここは……。 わしは いったい、 なにを していたのだ……。' },
      { who: 'ヴァルザード', text: 'そうか。 わしは ながい あいだ、 やみに こころを しばられて いたのだな。' },
      { who: 'ヴァルザード', text: 'わしを あやつっていたのは 「混沌王ゼノス」。 みなみの うみの はてに うかぶ 「闇の島」の あるじだ。' },
      { who: 'ヴァルザード', text: 'ゼノスは ひがしの 灼砂の島、 きたの 氷雪の島、 にしの 炎獄の島 —— 三つの しまの せいれいを とらえ、 その ちからで 闇の島に けっかいを はっておる。' },
      { who: 'ヴァルザード', text: 'せいれいを ときはなち、 三つの 「せいれいの ほうじゅ」を あつめれば、 けっかいは やぶれよう。' },
      { who: 'ヴァルザード', text: 'ゆうしゃよ。 わびの しるしに、 わが つばさを かそう。 わしの せなかに のれ。 どの しまへでも つれていこう。' },
    ]);
    const ids = g.state.party.map((m) => m.id);
    const lines = [];
    if (ids.includes('milia')) lines.push({ who: 'ミリア', text: 'りゅうの せなかに のれるの！？ すごい すごい！' });
    if (ids.includes('gald')) lines.push({ who: 'ガルド', text: 'まさか 魔竜と 手を くむ ことに なるとはな……。 だが わるくない。' });
    if (ids.includes('serena')) lines.push({ who: 'セレナ', text: 'せいれいたちの なげきが きこえます。 たすけに いきましょう。' });
    if (lines.length) await this.say(lines);
    this.running = false;
    g.cine = null;
  }

  /** 第二部のはじまり（城の前。竜が待っている） */
  async sequelStart() {
    const g = this.g, f = this.f;
    await this.begin();
    g.parkDragonNear();
    const fp = g.flight.parked.pos;
    this.cam(fp.clone().add(V(-12, 7, 14)), fp.clone().add(V(0, 3, 0)), 1.2);
    await sleep(600);
    await this.say([
      { text: '—— そして、 あたらしい たびが はじまる。' },
      { who: 'ヴァルザード', text: 'まずは ひがしの 灼砂の島へ むかうがよい。 つかれたら いつでも わしを よべ。' },
      { text: '（ちかくの ヴァルザードに はなしかけるか、 MENU の 「ドラゴン」で のることが できます）' },
      { text: '（そらの うえでは スティックで せんかい、 しまの うえで A を おすと おりられます。 MENU で うみの ちず）' },
    ]);
    this.end();
  }

  /** 島に はじめて おりたとき */
  async onLand(id) {
    const g = this.g, fl = this.flags;
    if (fl['land_' + id] || id === 'main') return;
    fl['land_' + id] = true;
    const T = {
      desert: [{ text: '（あつい かぜが すなを まきあげる。 ここは 灼砂の島 サンドラ。）' },
        { who: 'ヴァルザード', text: 'すなの せいれいは ファラオの ピラミッドの おくに とらわれておる。 まずは オアシスの町で ようすを きくがよい。' }],
      ice: [{ text: '（はく いきが しろい。 ここは 氷雪の島 フロスティア。）' },
        { who: 'ヴァルザード', text: 'きたの こおりの きゅうでんから、 こおりの せいれいの けはいが する。 さむさで たおれるでないぞ。' }],
      volcano: [{ text: '（じめんの したで マグマが うなっている。 ここは 炎獄の島 ボルカニア。）' },
        { who: 'ヴァルザード', text: 'ほのおの せいれいは ひのやまの どうくつの おく。 かじやの里で そうびを ととのえよ。' }],
      dark: [{ text: '（そらが くらい……。 ここが 混沌王の すむ 闇の島 ネクロス。）' },
        { who: 'ヴァルザード', text: 'ゼノスは しまの きたの こんとんの しろに いる。 ちかくに ひとの けはい…… レジスタンスの 砦が あるようだ。' }],
    }[id];
    if (!T) return;
    g.mode = 'cutscene';
    await this.say(T);
    if (g.mode === 'cutscene') g.mode = 'field';
  }

  /** 島のボスを倒した：せいれいが解き放たれ、ほうじゅを授かる */
  async spiritEvent(id) {
    const g = this.g, s = g.state, f = this.f;
    await this.begin();
    const info = {
      desert: { name: 'すなの せいれい', orb: 'すなの ほうじゅ', col: 0xffd27a, cols: [0xffd27a, 0xffffff, 0xffa040] },
      ice: { name: 'こおりの せいれい', orb: 'こおりの ほうじゅ', col: 0x9fe0ff, cols: [0x9fe0ff, 0xffffff, 0x60a0ff] },
      volcano: { name: 'ほのおの せいれい', orb: 'ほのおの ほうじゅ', col: 0xff8a30, cols: [0xff8a30, 0xffe0a0, 0xff4010] },
    }[id];
    const p = f.pos.clone().add(V(Math.sin(f.facing) * 4, 1.8, Math.cos(f.facing) * 4));
    const orb = new THREE.Mesh(new THREE.IcosahedronGeometry(0.5, 3), new THREE.MeshStandardMaterial({ color: info.col, emissive: info.col, emissiveIntensity: 3, roughness: 0.2 }));
    orb.position.copy(p);
    g.scene.add(orb);
    const tick = (dt) => { orb.rotation.y += dt; orb.position.y = p.y + Math.sin(performance.now() / 400) * 0.15; g.fx.flashLight(orb.position, info.col, 40, 0.1); };
    g.tickers.add(tick);
    this.cam(f.pos.clone().add(V(Math.sin(f.facing + 2.4) * 7, 4, Math.cos(f.facing + 2.4) * 7)), p, 1.5);
    g.audio.sfx('light');
    g.fx.emit({ pos: p, count: 160, color: info.cols, speed: 2, up: 1.5, life: 1.8, size: 0.35, spread: 1.4, flicker: 15 });
    await this.say([
      { who: info.name, text: '……ありがとう、 ひかりの ものたち。 ゼノスの くさりから ときはなたれました。' },
      { who: info.name, text: 'わたしの ちからを この 「ほうじゅ」に こめます。 どうか こんとんを とめてください。' },
    ]);
    s.flags['orb_' + id] = true;
    await g.audio.jingle('levelup', g.fieldMusic());
    await this.say(`${s.name}は 「${info.orb}」を てにいれた！`);
    g.tickers.delete(tick);
    g.scene.remove(orb);
    const n = ['desert', 'ice', 'volcano'].filter((k) => s.flags['orb_' + k]).length;
    if (n >= 3) {
      s.flags.darkOpen = true;
      g.ui.flashScreen('#c080ff', 900, 0.6);
      await this.say([{ text: 'みっつの ほうじゅが ひびきあい、 まばゆい ひかりを はなった！' }, { text: '（みなみの 闇の島の けっかいが きえた きが する……！）' }]);
    } else {
      await this.say([{ text: `（のこる ほうじゅは あと ${3 - n}つ。 ヴァルザードの もとへ もどろう。）` }]);
    }
    this.end();
  }

  /** 最後の戦いの前 */
  async beforeZenos() {
    const ids = this.g.state.party.map((m) => m.id);
    const lines = [{ who: this.g.state.name, text: '（みんなの ひかりを ひとつに……！）' }];
    if (ids.includes('milia')) lines.push({ who: 'ミリア', text: 'こんとんなんかに まけない。 わたしたちの せかいは わたしたちが まもる！' });
    if (ids.includes('gald')) lines.push({ who: 'ガルド', text: 'ヴァルザードの ぶんまで、 きっちり おとしまえを つけてやる！' });
    if (ids.includes('serena')) lines.push({ who: 'セレナ', text: 'せいれいたちよ…… さいごの ちからを！' });
    await this.say(lines);
  }

  /** ゼノスを倒した */
  async finalEnding() {
    const g = this.g, ui = g.ui;
    await this.begin();
    const z = this.f.ibossObj && this.f.ibossObj.root.visible ? this.f.ibossObj : null;
    await this.say([
      { who: 'ゼノス', text: 'ばかな…… ひかりが…… こんとんを こえる だと……。' },
      { who: 'ゼノス', text: '……おぼえておけ。 ひかりが あるかぎり、 やみも また きえは しないのだ……。' },
    ]);
    if (z) z.root.visible = false;
    g.ui.flashScreen('#ffffff', 1600, 1);
    g.audio.sfx('roar');
    await this.say([{ text: 'こんとんの しろが くずれはじめた！' }, { who: 'ヴァルザード', text: 'ゆうしゃよ、 こっちだ！ わが せなかに！' }]);
    await ui.fadeTo(1, 1400);
    this.running = false;
    g.cine = null;
    await g.finale();
  }

  /** 最後のエンディングで語られる仲間のその後 */
  finalEpilogue() {
    const ids = this.g.state.party.map((m) => m.id);
    const out = [{ who: 'ヴァルザード', text: 'わしは この そらから せかいを みまもろう。 よぶ こえが あれば、 いつでも かけつける。' }];
    if (ids.includes('milia')) out.push({ who: 'ミリア', text: 'わたし、 せかいいちの まほうつかいに なる！ そのときは また いっしょに たびしようね！' });
    if (ids.includes('gald')) out.push({ who: 'ガルド', text: 'おれは 騎士団に もどるぜ。 この 国も、 竜の とぶ そらも、 おれが まもる。' });
    if (ids.includes('serena')) out.push({ who: 'セレナ', text: 'せいれいたちと ともに、 ひかりの神殿を たてなおします。' });
    return out;
  }

  /** エンディングで語られる仲間のその後 */
  epilogue() {
    const ids = this.g.state.party.map((m) => m.id);
    const out = [];
    if (ids.includes('milia')) out.push({ who: 'ミリア', text: 'わたし、 もっと すごい まほうつかいに なる！ そのときは また いっしょに たびしようね！' });
    if (ids.includes('gald')) out.push({ who: 'ガルド', text: 'おれは もういちど 騎士団に もどるぜ。 王さま、 この 国は おれが まもる。' });
    if (ids.includes('serena')) out.push({ who: 'セレナ', text: 'ひかりの神殿を たてなおします。 いつでも いのりに きてくださいね。' });
    return out;
  }
}
