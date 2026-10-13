import { SPELLS, ITEMS, EQUIP, SHOP, SHOPS, MEMBERS, expForLevel, MAX_LV } from './data.js';
import { derived, knownSpells, save, memberName, healAll } from './state.js';
import { QUALITY, saveQualityKey, loadQualityKey } from '../core/renderer.js';

const R = 'calc(14px + var(--sar) + var(--btnw))';
const T = 'calc(min(170px, 36vh) + var(--sat))';
const R2 = 'calc(10em + var(--sar) + var(--btnw))';
const rint = (a, b) => Math.floor(a + Math.random() * (b - a + 1));

/** パーティから 1 人選ぶ（filter で選べない人を灰色に） */
async function pickMember(g, title, filter = () => true, sub = (m) => `H ${m.hp}`, pos = {}) {
  const s = g.state;
  if (s.party.length === 1 && filter(s.party[0])) return s.party[0];
  const j = await g.ui.choose(s.party.map((m) => ({ label: memberName(s, m), sub: sub(m), disabled: !filter(m) })),
    { right: R2, top: T, title, ...pos });
  return j < 0 ? null : s.party[j];
}

/** フィールドのメニュー */
export async function fieldMenu(g) {
  const ui = g.ui, s = g.state;
  let last = 0;
  for (;;) {
    const i = await ui.choose([
      { label: 'じゅもん' }, { label: 'どうぐ' }, { label: 'そうび' }, { label: 'つよさ' }, { label: 'ならびかえ', disabled: s.party.length < 2 },
      { label: 'せってい' }, { label: s.flags.sequel ? 'ドラゴン' : 'とじる' }, ...(s.flags.sequel ? [{ label: 'とじる' }] : []),
    ], { right: R, top: T, title: s.name, start: last });
    last = i;
    if (i < 0 || (i === 6 && !s.flags.sequel) || i === 7) return;
    if (i === 6) { await g.callDragon(); return; }
    if (i === 0) await spellMenu(g);
    if (i === 1) await itemMenu(g);
    if (i === 2) await equipMenu(g);
    if (i === 3) await statusWin(g);
    if (i === 4) await orderMenu(g);
    if (i === 5) await settingsMenu(g);
    g.hud.update();
  }
}

async function spellMenu(g) {
  const ui = g.ui, s = g.state;
  const caster = await pickMember(g, 'だれが？', (m) => m.hp > 0 && knownSpells(m).some((k) => SPELLS[k].field), (m) => `M ${m.mp}`);
  if (!caster) return;
  const list = knownSpells(caster).filter((k) => SPELLS[k].field);
  const j = await ui.choose(list.map((k) => ({ label: SPELLS[k].name, sub: SPELLS[k].mp, disabled: caster.mp < SPELLS[k].mp, desc: SPELLS[k].desc })),
    { right: 'calc(20em + var(--sar) + var(--btnw))', top: T, title: `MP ${caster.mp}` });
  if (j < 0) return;
  const k = list[j], sp = SPELLS[k];
  const cname = memberName(s, caster);
  if (k === 'warp') { caster.mp -= sp.mp; g.audio.sfx('spell'); await ui.say(`${cname}は ${sp.name}を となえた！`); await g.warpToCastle(); return; }
  if (sp.target === 'allies') {
    caster.mp -= sp.mp;
    g.audio.sfx('heal');
    for (const m of s.party) if (m.hp > 0) m.hp = Math.min(derived(m).maxHp, m.hp + rint(...sp.power));
    g.hud.update();
    await ui.say([`${cname}は ${sp.name}を となえた！`, 'なかまたちの HPが かいふくした！']);
    return;
  }
  const dead = sp.target === 'dead';
  const t = await pickMember(g, 'だれに？', (m) => (dead ? m.hp <= 0 : m.hp > 0), undefined, { right: 'calc(20em + var(--sar) + var(--btnw))' });
  if (!t) return;
  caster.mp -= sp.mp;
  g.audio.sfx(dead ? 'light' : 'heal');
  if (dead) t.hp = Math.ceil(derived(t).maxHp / 2);
  const v = dead ? t.hp : Math.min(derived(t).maxHp - t.hp, rint(...sp.power));
  if (!dead) t.hp += v;
  g.fx.emit({ pos: g.field.pos.clone().setY(g.field.pos.y + 0.2), count: 70, color: [0x9dffb0, 0xffffff], speed: 0.6, up: 2.2, life: 1.3, size: 0.25, spread: 1.4, flicker: 20 });
  g.hud.update();
  await ui.say([`${cname}は ${sp.name}を となえた！`, dead ? `${memberName(s, t)}が いきかえった！` : `${memberName(s, t)}の HPが ${v} かいふくした！`]);
}

async function itemMenu(g) {
  const ui = g.ui, s = g.state;
  const list = Object.entries(s.items).filter(([, n]) => n > 0);
  if (!list.length) { await ui.say('なにも もっていない。'); return; }
  const j = await ui.choose(list.map(([k, n]) => ({ label: ITEMS[k].name, sub: `×${n}`, desc: ITEMS[k].desc })), { right: R2, top: T, title: 'どうぐ' });
  if (j < 0) return;
  const [k] = list[j], it = ITEMS[k];
  if (it.use === 'warp') {
    s.items[k]--;
    await ui.say(`${s.name}は ${it.name}を そらに なげた！`);
    await g.warpToCastle();
    return;
  }
  const t = await pickMember(g, 'だれに？', (m) => m.hp > 0, it.use === 'mp' ? (m) => `M ${m.mp}` : undefined, { right: 'calc(20em + var(--sar) + var(--btnw))' });
  if (!t) return;
  s.items[k]--;
  const d = derived(t);
  if (it.use === 'heal') {
    const v = Math.min(d.maxHp - t.hp, rint(...it.power));
    t.hp += v;
    g.audio.sfx('heal');
    await ui.say([`${it.name}を つかった！`, `${memberName(s, t)}の HPが ${v} かいふくした！`]);
  } else if (it.use === 'mp') {
    const v = Math.min(d.maxMp - t.mp, it.power[0]);
    t.mp += v;
    g.audio.sfx('heal');
    await ui.say([`${memberName(s, t)}は ${it.name}を のんだ！`, `MPが ${v} かいふくした！`]);
  }
  g.hud.update();
}

async function equipMenu(g) {
  const ui = g.ui, s = g.state;
  const who = await pickMember(g, 'だれの？', () => true, (m) => MEMBERS[m.id].role);
  if (!who) return;
  const slots = [['weapon', 'ぶき'], ['armor', 'よろい'], ['shield', 'たて']];
  let last = 0;
  for (;;) {
    const i = await ui.choose(slots.map(([k, n]) => ({ label: n, sub: EQUIP[who.equip[k]] ? EQUIP[who.equip[k]].name : 'なし' })),
      { right: 'calc(20em + var(--sar) + var(--btnw))', top: T, title: memberName(s, who), start: last });
    if (i < 0) return;
    last = i;
    const slot = slots[i][0];
    const options = [who.equip[slot], ...s.bag.filter((k) => EQUIP[k].slot === slot)].filter(Boolean);
    if (!options.length) { await ui.say('そうび できるものが ない。'); continue; }
    const j = await ui.choose(options.map((k) => ({ label: (k === who.equip[slot] ? 'E ' : '　') + EQUIP[k].name, sub: EQUIP[k].atk ? `こうげき+${EQUIP[k].atk}` : `しゅび+${EQUIP[k].def}` })),
      { right: 'calc(20em + var(--sar) + var(--btnw))', top: 'calc(min(330px, 52vh) + var(--sat))', title: slots[i][1] });
    if (j < 0) continue;
    const k = options[j];
    if (k === who.equip[slot]) {
      // はずす
      s.bag.push(k);
      who.equip[slot] = null;
      g.audio.sfx('cancel');
      continue;
    }
    s.bag.splice(s.bag.indexOf(k), 1);
    if (who.equip[slot]) s.bag.push(who.equip[slot]);
    who.equip[slot] = k;
    g.audio.sfx('item');
    await ui.say(`${memberName(s, who)}は ${EQUIP[k].name}を そうびした。`);
  }
}

async function orderMenu(g) {
  const s = g.state;
  const a = await pickMember(g, 'だれと？', (m) => m.id !== 'hero', (m) => MEMBERS[m.id].role);
  if (!a) return;
  const b = await pickMember(g, 'いれかえる', (m) => m.id !== 'hero' && m !== a, (m) => MEMBERS[m.id].role, { right: 'calc(20em + var(--sar) + var(--btnw))' });
  if (!b) return;
  const ia = s.party.indexOf(a), ib = s.party.indexOf(b);
  s.party[ia] = b; s.party[ib] = a;
  g.field.resetFollowers();
  g.audio.sfx('confirm');
}

export async function statusWin(g, who) {
  const s = g.state;
  const m = who || await pickMember(g, 'だれの？', () => true, (x) => `Lv ${x.lv}`);
  if (!m) return;
  const d = derived(m);
  const next = m.lv >= MAX_LV ? '-' : expForLevel(m.lv + 1) - m.exp;
  const eq = (k) => (m.equip[k] && EQUIP[m.equip[k]] ? EQUIP[m.equip[k]].name : 'なし');
  const w = g.ui.window(`
    <div class="title">つよさ</div>
    <table>
      <tr><td>なまえ</td><td>${memberName(s, m)}（${MEMBERS[m.id].role}）</td></tr>
      <tr><td>レベル</td><td>${m.lv}</td></tr>
      <tr><td>HP</td><td>${m.hp} / ${d.maxHp}</td></tr>
      <tr><td>MP</td><td>${m.mp} / ${d.maxMp}</td></tr>
      <tr><td>ちから</td><td>${d.str}</td></tr>
      <tr><td>すばやさ</td><td>${d.agi}</td></tr>
      <tr><td>こうげき力</td><td>${d.atk}</td></tr>
      <tr><td>しゅび力</td><td>${d.def}</td></tr>
      <tr><td>ぶき／よろい／たて</td><td>${eq('weapon')}／${eq('armor')}／${eq('shield')}</td></tr>
      <tr><td>つぎのレベルまで</td><td>${next}</td></tr>
      <tr><td>ゴールド</td><td>${s.gold} G</td></tr>
    </table>`, { id: 'stats' });
  await g.ui.waitKey(w);
}

async function settingsMenu(g) {
  const ui = g.ui;
  for (;;) {
    const qk = loadQualityKey();
    const i = await ui.choose([
      { label: 'がしつ', sub: QUALITY[qk].label },
      { label: 'BGM', sub: g.audio.musicVol > 0 ? 'ON' : 'OFF' },
      { label: 'もじの はやさ', sub: g.ui.textSpeed > 30 ? 'はやい' : 'ふつう' },
      { label: 'もどる' },
    ], { right: R2, top: T, title: 'せってい' });
    if (i < 0 || i === 3) return;
    if (i === 0) {
      const keys = Object.keys(QUALITY);
      const j = await ui.choose(keys.map((k) => ({ label: QUALITY[k].label, sub: k === qk ? '●' : '' })), { right: 'calc(20em + var(--sar) + var(--btnw))', top: T, title: 'がしつ' });
      if (j >= 0 && keys[j] !== qk) {
        saveQualityKey(keys[j]);
        save(g.snapshot());
        await ui.say('がしつを かえるため さいきどう します。（ぼうけんは そのまま つづけられます）');
        location.reload();
      }
    }
    if (i === 1) {
      g.audio.musicVol = g.audio.musicVol > 0 ? 0 : 0.8;
      if (g.audio.music) g.audio.music.gain.value = g.audio.musicVol;
    }
    if (i === 2) g.ui.textSpeed = g.ui.textSpeed > 30 ? 28 : 60;
  }
}

/** 宿屋（全員回復・たおれた仲間も目をさます） */
export async function inn(g) {
  const ui = g.ui, s = g.state;
  const price = (6 * s.party.length + 4) * ({ desert: 3, ice: 4, volcano: 6, dark: 8 }[g.world.map.id] || 1);
  const w = await ui.say({ who: 'やどや', text: `たびびとの やどやへ ようこそ。 ひとばん ${price}ゴールドですが おとまりに なりますか？` }, { keep: true });
  const yes = await ui.yesno();
  w.remove();
  if (!yes) { await ui.say({ who: 'やどや', text: 'またの おこしを おまちしております。' }); return; }
  if (s.gold < price) { await ui.say({ who: 'やどや', text: 'おや、 おかねが たりない ようですね。' }); return; }
  s.gold -= price;
  await ui.say({ who: 'やどや', text: 'では ごゆっくり おやすみください。' });
  g.audio.stop(0.6);
  await ui.fadeTo(1, 900);
  healAll(s);
  g.sky.time = 0.27;
  g.sky.envTimer = 999;
  g.hud.update();
  await g.audio.jingle('inn', null);
  await ui.fadeTo(0, 1200);
  g.updateMusic(true);
  save(g.snapshot());
  await ui.say({ who: 'やどや', text: 'おはよう ございます。 ゆうべは よく おやすみ でしたね。 （ぼうけんを きろくしました）' });
}

/** 武器・防具・道具屋 */
export async function shop(g, where = 'main') {
  const ui = g.ui, s = g.state;
  const LIST = SHOPS[where] || SHOP;
  await ui.say({ who: 'しょうにん', text: 'いらっしゃい！ ぶきと ぼうぐと どうぐの みせだよ。' });
  for (;;) {
    const i = await ui.choose([{ label: 'かう' }, { label: 'うる' }, { label: 'やめる' }], { right: R, top: T, title: `${s.gold} G` });
    if (i < 0 || i === 2) break;
    if (i === 0) {
      for (;;) {
        const items = LIST.map((k) => {
          const it = ITEMS[k] || EQUIP[k];
          return { label: it.name, sub: `${it.price}G`, desc: ITEMS[k] ? it.desc : EQUIP[k].atk ? `こうげき力 +${EQUIP[k].atk}` : `しゅび力 +${EQUIP[k].def}` };
        });
        const j = await ui.choose(items, { right: 'calc(8em + var(--sar) + var(--btnw))', top: 'calc(min(60px, 12vh) + var(--sat))', title: `${s.gold} G` });
        if (j < 0) break;
        const k = LIST[j];
        const it = ITEMS[k] || EQUIP[k];
        if (s.gold < it.price) { await ui.say({ who: 'しょうにん', text: 'おかねが たりないようだね。' }); continue; }
        s.gold -= it.price;
        g.audio.sfx('coin');
        if (ITEMS[k]) { g.addItem(k, 1); await ui.say({ who: 'しょうにん', text: `${it.name}だね。 まいどあり！` }); continue; }
        s.bag.push(k);
        const w = await ui.say({ who: 'しょうにん', text: `${it.name}だね。 いま そうびしていくかい？` }, { keep: true });
        const yes = await ui.yesno();
        w.remove();
        if (yes) {
          const who = await pickMember(g, 'だれが？', () => true, (m) => { const e = m.equip[EQUIP[k].slot]; return e ? EQUIP[e].name : 'なし'; });
          if (who) {
            const slot = EQUIP[k].slot;
            s.bag.splice(s.bag.indexOf(k), 1);
            if (who.equip[slot]) s.bag.push(who.equip[slot]);
            who.equip[slot] = k;
            g.audio.sfx('item');
            await ui.say(`${memberName(s, who)}は ${it.name}を そうびした。`);
          }
        }
      }
    } else {
      const list = [...Object.entries(s.items).filter(([, n]) => n > 0).map(([k]) => k), ...s.bag];
      if (!list.length) { await ui.say({ who: 'しょうにん', text: 'うれる ものが ないみたいだね。' }); continue; }
      const j = await ui.choose(list.map((k) => { const it = ITEMS[k] || EQUIP[k]; return { label: it.name, sub: `${Math.floor(it.price / 2)}G` }; }),
        { right: 'calc(8em + var(--sar) + var(--btnw))', top: 'calc(min(60px, 12vh) + var(--sat))', title: 'うる' });
      if (j < 0) continue;
      const k = list[j];
      const it = ITEMS[k] || EQUIP[k];
      if (ITEMS[k]) s.items[k]--; else s.bag.splice(s.bag.indexOf(k), 1);
      s.gold += Math.floor(it.price / 2);
      g.audio.sfx('coin');
      await ui.say({ who: 'しょうにん', text: `${it.name}を ${Math.floor(it.price / 2)}ゴールドで かいとろう。` });
    }
  }
  await ui.say({ who: 'しょうにん', text: 'まいど！ また きておくれ。' });
}
