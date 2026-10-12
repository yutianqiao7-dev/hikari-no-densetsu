import { statsForLevel, expForLevel, EQUIP, SPELLS, MAX_LV } from './data.js';

const KEY = 'hikari_save_v1';

export function newState(name = 'ユウト') {
  const st = statsForLevel(1);
  return {
    name,
    lv: 1, exp: 0, gold: 0,
    hp: st.maxHp, mp: st.maxMp,
    items: { herb: 2 },
    equip: { weapon: 'sword_copper', armor: 'armor_cloth', shield: 'shield_leather' },
    bag: [],   // 装備していない装備品
    flags: {},
    pos: null,
    time: 0.3,
    playTime: 0,
  };
}

export function derived(s) {
  const b = statsForLevel(s.lv);
  const w = EQUIP[s.equip.weapon], a = EQUIP[s.equip.armor], sh = EQUIP[s.equip.shield];
  return {
    ...b,
    atk: b.str + (w ? w.atk : 0),
    def: Math.round(b.agi / 2) + (a ? a.def : 0) + (sh ? sh.def : 0),
  };
}

export function knownSpells(s) {
  return Object.entries(SPELLS).filter(([, sp]) => s.lv >= sp.lv).map(([k]) => k);
}

/** 経験値を加え、上がったレベルごとの変化を返す */
export function gainExp(s, exp) {
  s.exp += exp;
  const ups = [];
  while (s.lv < MAX_LV && s.exp >= expForLevel(s.lv + 1)) {
    const before = statsForLevel(s.lv);
    const spellsBefore = knownSpells(s);
    s.lv += 1;
    const after = statsForLevel(s.lv);
    s.hp += after.maxHp - before.maxHp;
    s.mp += after.maxMp - before.maxMp;
    const learned = knownSpells(s).filter((k) => !spellsBefore.includes(k));
    ups.push({ lv: s.lv, d: { str: after.str - before.str, agi: after.agi - before.agi, maxHp: after.maxHp - before.maxHp, maxMp: after.maxMp - before.maxMp }, learned });
  }
  return ups;
}

export function save(s) {
  try { localStorage.setItem(KEY, JSON.stringify(s)); return true; } catch { return false; }
}
export function load() {
  try { const t = localStorage.getItem(KEY); return t ? JSON.parse(t) : null; } catch { return null; }
}
export function hasSave() { return !!load(); }
