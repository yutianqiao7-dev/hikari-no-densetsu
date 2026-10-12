import { SPELLS, ITEMS, EQUIP, SHOP, expForLevel, MAX_LV } from './data.js';
import { derived, knownSpells, save } from './state.js';
import { QUALITY, saveQualityKey, loadQualityKey } from '../core/renderer.js';

const R = 'calc(14px + var(--sar))';
const T = 'calc(160px + var(--sat))';

/** フィールドのメニュー */
export async function fieldMenu(g) {
  const ui = g.ui, s = g.state;
  let last = 0;
  for (;;) {
    const i = await ui.choose([
      { label: 'じゅもん' }, { label: 'どうぐ' }, { label: 'そうび' }, { label: 'つよさ' }, { label: 'せってい' }, { label: 'とじる' },
    ], { right: R, top: T, title: s.name, start: last });
    last = i;
    if (i < 0 || i === 5) return;
    if (i === 0) await spellMenu(g);
    if (i === 1) await itemMenu(g);
    if (i === 2) await equipMenu(g);
    if (i === 3) await statusWin(g);
    if (i === 4) await settingsMenu(g);
  }
}

async function spellMenu(g) {
  const ui = g.ui, s = g.state;
  const list = knownSpells(s).filter((k) => SPELLS[k].field);
  if (!list.length) { await ui.say('つかえる じゅもんが ない。'); return; }
  const j = await ui.choose(list.map((k) => ({ label: SPELLS[k].name, sub: SPELLS[k].mp, disabled: s.mp < SPELLS[k].mp, desc: SPELLS[k].desc })),
    { right: 'calc(10em + var(--sar))', top: T, title: `MP ${s.mp}` });
  if (j < 0) return;
  const k = list[j], sp = SPELLS[k];
  s.mp -= sp.mp;
  g.audio.sfx('spell');
  if (k === 'warp') { await ui.say(`${s.name}は ${sp.name}を となえた！`); await g.warpToCastle(); return; }
  const d = derived(s);
  const v = Math.min(d.maxHp - s.hp, Math.round(sp.power[0] + Math.random() * (sp.power[1] - sp.power[0])));
  s.hp += v;
  g.fx.emit({ pos: g.field.pos.clone().setY(g.field.pos.y + 0.2), count: 70, color: [0x9dffb0, 0xffffff], speed: 0.6, up: 2.2, life: 1.3, size: 0.25, spread: 1.4, flicker: 20 });
  g.audio.sfx('heal');
  g.hud.update();
  await ui.say([`${s.name}は ${sp.name}を となえた！`, `HPが ${v} かいふくした！`]);
}

async function itemMenu(g) {
  const ui = g.ui, s = g.state;
  const list = Object.entries(s.items).filter(([, n]) => n > 0);
  if (!list.length) { await ui.say('なにも もっていない。'); return; }
  const j = await ui.choose(list.map(([k, n]) => ({ label: ITEMS[k].name, sub: `×${n}`, desc: ITEMS[k].desc })),
    { right: 'calc(10em + var(--sar))', top: T, title: 'どうぐ' });
  if (j < 0) return;
  const [k] = list[j], it = ITEMS[k];
  s.items[k]--;
  const d = derived(s);
  if (it.use === 'heal') {
    const v = Math.min(d.maxHp - s.hp, Math.round(it.power[0] + Math.random() * (it.power[1] - it.power[0])));
    s.hp += v;
    g.audio.sfx('heal');
    g.hud.update();
    await ui.say([`${s.name}は ${it.name}を つかった！`, `HPが ${v} かいふくした！`]);
  } else if (it.use === 'mp') {
    const v = Math.min(d.maxMp - s.mp, it.power[0]);
    s.mp += v;
    g.audio.sfx('heal');
    g.hud.update();
    await ui.say([`${s.name}は ${it.name}を のんだ！`, `MPが ${v} かいふくした！`]);
  } else if (it.use === 'warp') {
    await ui.say(`${s.name}は ${it.name}を そらに なげた！`);
    await g.warpToCastle();
  }
}

async function equipMenu(g) {
  const ui = g.ui, s = g.state;
  const slots = [['weapon', 'ぶき'], ['armor', 'よろい'], ['shield', 'たて']];
  let last = 0;
  for (;;) {
    const i = await ui.choose(slots.map(([k, n]) => ({ label: n, sub: EQUIP[s.equip[k]] ? EQUIP[s.equip[k]].name : 'なし' })),
      { right: 'calc(10em + var(--sar))', top: T, title: 'そうび', start: last });
    if (i < 0) return;
    last = i;
    const slot = slots[i][0];
    const options = [s.equip[slot], ...s.bag.filter((k) => EQUIP[k].slot === slot)].filter(Boolean);
    const j = await ui.choose(options.map((k) => ({ label: (k === s.equip[slot] ? 'E ' : '　') + EQUIP[k].name, sub: EQUIP[k].atk ? `こうげき+${EQUIP[k].atk}` : `しゅび+${EQUIP[k].def}` })),
      { right: 'calc(10em + var(--sar))', top: 'calc(320px + var(--sat))', title: slots[i][1] });
    if (j <= 0) continue;
    const k = options[j];
    s.bag.splice(s.bag.indexOf(k), 1);
    s.bag.push(s.equip[slot]);
    s.equip[slot] = k;
    g.audio.sfx('item');
    await ui.say(`${s.name}は ${EQUIP[k].name}を そうびした。`);
  }
}

export async function statusWin(g) {
  const s = g.state, d = derived(s);
  const next = s.lv >= MAX_LV ? '-' : expForLevel(s.lv + 1) - s.exp;
  const w = g.ui.window(`
    <div class="title">つよさ</div>
    <table>
      <tr><td>なまえ</td><td>${s.name}</td></tr>
      <tr><td>レベル</td><td>${s.lv}</td></tr>
      <tr><td>HP</td><td>${s.hp} / ${d.maxHp}</td></tr>
      <tr><td>MP</td><td>${s.mp} / ${d.maxMp}</td></tr>
      <tr><td>ちから</td><td>${d.str}</td></tr>
      <tr><td>すばやさ</td><td>${d.agi}</td></tr>
      <tr><td>こうげき力</td><td>${d.atk}</td></tr>
      <tr><td>しゅび力</td><td>${d.def}</td></tr>
      <tr><td>けいけんち</td><td>${s.exp}</td></tr>
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
    ], { right: 'calc(10em + var(--sar))', top: T, title: 'せってい' });
    if (i < 0 || i === 3) return;
    if (i === 0) {
      const keys = Object.keys(QUALITY);
      const j = await ui.choose(keys.map((k) => ({ label: QUALITY[k].label, sub: k === qk ? '●' : '' })), { right: 'calc(20em + var(--sar))', top: T, title: 'がしつ' });
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

/** 宿屋 */
export async function inn(g) {
  const ui = g.ui, s = g.state;
  const price = 10;
  const w = await ui.say({ who: 'やどや', text: `たびびとの やどやへ ようこそ。 ひとばん ${price}ゴールドですが おとまりに なりますか？` }, { keep: true });
  const yes = await ui.yesno();
  w.remove();
  if (!yes) { await ui.say({ who: 'やどや', text: 'またの おこしを おまちしております。' }); return; }
  if (s.gold < price) { await ui.say({ who: 'やどや', text: 'おや、 おかねが たりない ようですね。' }); return; }
  s.gold -= price;
  await ui.say({ who: 'やどや', text: 'では ごゆっくり おやすみください。' });
  g.audio.stop(0.6);
  await ui.fadeTo(1, 900);
  const d = derived(s);
  s.hp = d.maxHp;
  s.mp = d.maxMp;
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
export async function shop(g) {
  const ui = g.ui, s = g.state;
  await ui.say({ who: 'しょうにん', text: 'いらっしゃい！ ぶきと ぼうぐと どうぐの みせだよ。' });
  for (;;) {
    const i = await ui.choose([{ label: 'かう' }, { label: 'うる' }, { label: 'やめる' }], { right: R, top: T, title: `${s.gold} G` });
    if (i < 0 || i === 2) break;
    if (i === 0) {
      for (;;) {
        const items = SHOP.map((k) => {
          const it = ITEMS[k] || EQUIP[k];
          const owned = EQUIP[k] && (s.bag.includes(k) || Object.values(s.equip).includes(k));
          return { label: it.name, sub: owned ? 'もっている' : `${it.price}G`, disabled: owned, desc: ITEMS[k] ? it.desc : EQUIP[k].atk ? `こうげき力 +${EQUIP[k].atk}` : `しゅび力 +${EQUIP[k].def}` };
        });
        const j = await ui.choose(items, { right: 'calc(8em + var(--sar))', top: 'calc(60px + var(--sat))', title: `${s.gold} G` });
        if (j < 0) break;
        const k = SHOP[j];
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
          const slot = EQUIP[k].slot;
          s.bag.splice(s.bag.indexOf(k), 1);
          s.bag.push(s.equip[slot]);
          s.equip[slot] = k;
          g.audio.sfx('item');
          await ui.say(`${s.name}は ${it.name}を そうびした。`);
        }
      }
    } else {
      const list = [...Object.entries(s.items).filter(([, n]) => n > 0).map(([k]) => k), ...s.bag];
      if (!list.length) { await ui.say({ who: 'しょうにん', text: 'うれる ものが ないみたいだね。' }); continue; }
      const j = await ui.choose(list.map((k) => { const it = ITEMS[k] || EQUIP[k]; return { label: it.name, sub: `${Math.floor(it.price / 2)}G` }; }),
        { right: 'calc(8em + var(--sar))', top: 'calc(60px + var(--sat))', title: 'うる' });
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
