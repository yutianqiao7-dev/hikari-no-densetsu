import { EQUIP, SPELLS, MAX_LV, expForLevel, MEMBERS } from './data.js';

const KEY = 'hikari_save_v1';

/** メンバー 1 人分 */
export function newMember(id, lv = 1) {
  const d = MEMBERS[id];
  const m = { id, lv: 1, exp: 0, hp: 1, mp: 0, equip: { ...d.equip } };
  while (m.lv < lv) m.lv++;
  m.exp = expForLevel(m.lv);
  const st = baseStats(m);
  m.hp = st.maxHp;
  m.mp = st.maxMp;
  return m;
}

export function newState(name = 'ユウト') {
  return {
    name,
    gold: 0,
    items: { herb: 2 },
    bag: [],   // 装備していない装備品（パーティ共有）
    flags: {},
    pos: null,
    time: 0.3,
    playTime: 0,
    party: [newMember('hero', 1)],
  };
}

/** 旧セーブ（勇者だけ）をパーティ形式に変換 */
export function migrate(s) {
  if (!s.party) {
    const hero = { id: 'hero', lv: s.lv || 1, exp: s.exp || 0, hp: s.hp || 1, mp: s.mp || 0, equip: s.equip || { ...MEMBERS.hero.equip } };
    s.party = [hero];
    for (const k of ['lv', 'exp', 'hp', 'mp', 'equip']) delete s[k];
  }
  return s;
}

export function memberName(state, m) { return m.id === 'hero' ? state.name : MEMBERS[m.id].name; }

function baseStats(m) {
  const d = MEMBERS[m.id], l = m.lv - 1;
  return {
    maxHp: Math.round(d.base.hp + l * d.grow.hp + Math.pow(l, 1.5) * d.grow.hp * 0.08),
    maxMp: Math.round(d.base.mp + l * d.grow.mp),
    str: Math.round(d.base.str + l * d.grow.str),
    agi: Math.round(d.base.agi + l * d.grow.agi),
  };
}

export function derived(m) {
  const b = baseStats(m);
  const w = EQUIP[m.equip.weapon], a = EQUIP[m.equip.armor], sh = EQUIP[m.equip.shield];
  return {
    ...b,
    atk: b.str + (w ? w.atk : 0),
    def: Math.round(b.agi / 2) + (a ? a.def : 0) + (sh ? sh.def : 0),
  };
}

export function knownSpells(m) {
  const learn = MEMBERS[m.id].spells;
  return Object.keys(learn).filter((k) => m.lv >= learn[k] && SPELLS[k]);
}

/** 経験値を加え、上がったレベルごとの変化を返す */
export function gainExp(m, exp) {
  m.exp += exp;
  const ups = [];
  while (m.lv < MAX_LV && m.exp >= expForLevel(m.lv + 1)) {
    const before = baseStats(m);
    const spellsBefore = knownSpells(m);
    m.lv += 1;
    const after = baseStats(m);
    m.hp += after.maxHp - before.maxHp;
    m.mp += after.maxMp - before.maxMp;
    const learned = knownSpells(m).filter((k) => !spellsBefore.includes(k));
    ups.push({ lv: m.lv, d: { str: after.str - before.str, agi: after.agi - before.agi, maxHp: after.maxHp - before.maxHp, maxMp: after.maxMp - before.maxMp }, learned });
  }
  return ups;
}

/** 仲間を加える（勇者のレベルに合わせる） */
export function addMember(state, id) {
  if (state.party.some((m) => m.id === id)) return null;
  const heroLv = state.party[0].lv;
  const m = newMember(id, Math.max(MEMBERS[id].minLv || 1, heroLv - 1));
  state.party.push(m);
  return m;
}

export function healAll(state) {
  for (const m of state.party) { const d = derived(m); m.hp = d.maxHp; m.mp = d.maxMp; }
}

export const alive = (state) => state.party.filter((m) => m.hp > 0);

export function save(s) {
  try { localStorage.setItem(KEY, JSON.stringify(s)); return true; } catch { return false; }
}
export function load() {
  try { const t = localStorage.getItem(KEY); return t ? migrate(JSON.parse(t)) : null; } catch { return null; }
}
export function hasSave() { return !!load(); }
