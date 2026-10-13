/**
 * オリジナル BGM と効果音（WebAudio シンセサイザー）
 * 音符表記: "C5:2" = C5 を 8分音符 2 つ分。"-:2" は休符。"C4+E4+G4:8" は和音。
 * ドラム: "k" キック, "s" スネア, "h" ハイハット, "o" オープンハット, "c" クラッシュ
 */
const NOTE = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
function freq(n) {
  const m = /^([A-G])(#|b)?(\d)$/.exec(n);
  if (!m) return 0;
  let s = NOTE[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0);
  const midi = (parseInt(m[3], 10) + 1) * 12 + s;
  return 440 * Math.pow(2, (midi - 69) / 12);
}
function parse(str) {
  const out = [];
  let t = 0;
  for (const tok of str.trim().split(/[\s|]+/)) {
    if (!tok) continue;
    const [n, l] = tok.split(':');
    const len = parseFloat(l || '1');
    if (n !== '-') out.push({ t, len, notes: n.split('+') });
    t += len;
  }
  return { events: out, length: t };
}
// コード進行から伴奏パターンを作るヘルパー
const CH = {
  F: ['F3', 'A3', 'C4'], Bb: ['Bb2', 'D3', 'F3'], Dm: ['D3', 'F3', 'A3'], C: ['C3', 'E3', 'G3'], Gm: ['G2', 'Bb2', 'D3'],
  G: ['G2', 'B2', 'D3'], D: ['D3', 'F#3', 'A3'], Am: ['A2', 'C3', 'E3'], Em: ['E3', 'G3', 'B3'], A: ['A2', 'C#3', 'E3'],
  E: ['E2', 'G#2', 'B2'], Bm: ['B2', 'D3', 'F#3'], 'F#m': ['F#2', 'A2', 'C#3'], Cmaj: ['C3', 'E3', 'G3'],
  Cm: ['C3', 'Eb3', 'G3'], Ab: ['Ab2', 'C3', 'Eb3'],
  B: ['B2', 'D#3', 'F#3'], Fm: ['F3', 'Ab3', 'C4'], Db: ['Db3', 'F3', 'Ab3'], Eb: ['Eb3', 'G3', 'Bb3'],
};
const up = (n, o) => n.replace(/\d/, (d) => String(parseInt(d, 10) + o));
function bassLine(chords, pat, bar) {
  return chords.map((c) => pat.map(([deg, len, oct]) => `${up(CH[c][deg], oct)}:${len}`).join(' ')).join(' | ') + (bar ? '' : '');
}
function padLine(chords, len, oct = 1) { return chords.map((c) => `${CH[c].map((n) => up(n, oct)).join('+')}:${len}`).join(' '); }
function arpLine(chords, pat, oct = 2) { return chords.map((c) => pat.map(([d, l]) => `${up(CH[c][d], oct)}:${l}`).join(' ')).join(' '); }
const rep = (s, n) => Array(n).fill(s).join(' ');

const FIELD_CH = ['F', 'Bb', 'F', 'Dm', 'Bb', 'F', 'C', 'F', 'Dm', 'F', 'Bb', 'F', 'Gm', 'C', 'Dm', 'F'];
const FIELD_MEL = `
  F4:2 A4:2 C5:3 A4:1 | Bb4:2 D5:2 C5:4 | A4:2 C5:2 F5:3 E5:1 | D5:2 C5:2 A4:4 |
  Bb4:2 C5:2 D5:3 Bb4:1 | C5:2 A4:2 F4:4 | G4:2 A4:1 Bb4:1 C5:2 E5:2 | F5:6 -:2 |
  D5:2 F5:2 E5:2 D5:2 | C5:3 A4:1 F4:4 | Bb4:2 D5:2 C5:2 Bb4:2 | A4:3 G4:1 F4:4 |
  G4:2 Bb4:2 A4:2 C5:2 | Bb4:2 D5:2 C5:2 E5:2 | F5:3 E5:1 D5:2 E5:2 | F5:8`;

const TOWN_CH = ['G', 'D', 'C', 'G', 'C', 'G', 'D', 'G'];
const TOWN_MEL = `
  B4:2 D5:2 G5:2 | F#5:3 E5:1 D5:2 | C5:2 E5:2 A5:2 | G5:6 |
  E5:2 G5:2 E5:2 | D5:2 B4:2 G4:2 | A4:2 B4:1 C5:1 D5:2 | G4:6 |
  B4:2 C5:2 D5:2 | A4:3 B4:1 C5:2 | G4:2 C5:2 E5:2 | D5:6 |
  E5:2 F#5:2 G5:2 | D5:3 C5:1 B4:2 | A4:2 D5:2 F#5:2 | G5:6`;

const CASTLE_CH = ['D', 'Bm', 'G', 'A', 'D', 'F#m', 'Em', 'A', 'G', 'D', 'Em', 'A', 'D', 'G', 'A', 'D'];
const CASTLE_MEL = `
  D5:4 A4:2 D5:2 | F#5:4 E5:2 D5:2 | G5:3 F#5:1 E5:2 D5:2 | E5:8 |
  F#5:4 D5:2 F#5:2 | A5:4 G5:2 F#5:2 | E5:2 F#5:2 G5:2 E5:2 | A5:8 |
  B5:4 A5:2 G5:2 | F#5:4 E5:2 D5:2 | G5:2 F#5:2 E5:2 G5:2 | A5:6 C#5:2 |
  D5:3 E5:1 F#5:2 A5:2 | B5:3 A5:1 G5:2 B5:2 | A5:2 G5:2 F#5:2 E5:2 | D5:8`;

const BATTLE_CH = ['Am', 'Am', 'F', 'G', 'Am', 'Am', 'F', 'E', 'F', 'G', 'Em', 'Am', 'F', 'G', 'A', 'E'];
const BATTLE_MEL = `
  A4:1 C5:1 E5:2 A5:2 G5:1 E5:1 | F5:3 E5:1 D5:2 C5:2 | D5:1 E5:1 F5:2 E5:2 C5:2 | B4:3 C5:1 D5:4 |
  A5:2 G5:1 F5:1 E5:2 C5:2 | D5:2 E5:2 F5:2 G5:2 | A5:3 G5:1 F5:2 D5:2 | E5:6 G#5:2 |
  A5:2 F5:2 C5:2 F5:2 | G5:2 D5:2 B4:2 D5:2 | E5:2 B4:2 G4:2 B4:2 | C5:2 E5:2 A5:4 |
  F5:1 G5:1 A5:2 F5:2 C5:2 | D5:1 E5:1 G5:2 D5:2 B4:2 | C#5:2 E5:2 A5:2 C#6:2 | B5:4 G#5:4`;

const BOSS_CH = ['Dm', 'Dm', 'Bb', 'A', 'Dm', 'Gm', 'A', 'A', 'Bb', 'C', 'Am', 'Dm', 'Gm', 'A', 'Dm', 'A'];
const BOSS_MEL = `
  D5:3 F5:1 A5:2 G#5:2 | A5:4 -:2 D6:2 | C6:2 Bb5:2 A5:2 G5:2 | A5:6 -:2 |
  F5:2 G5:2 A5:2 Bb5:2 | C6:3 Bb5:1 A5:4 | G5:2 F5:2 E5:2 C#5:2 | E5:8 |
  D6:2 C6:2 Bb5:2 F5:2 | E5:2 G5:2 C6:4 | C6:2 A5:2 E5:2 A5:2 | D6:6 -:2 |
  Bb5:2 A5:2 G5:2 D5:2 | C#5:2 E5:2 A5:4 | F5:2 E5:2 D5:2 F5:2 | E5:4 C#5:4`;

const CAVE_CH = ['Dm', 'Dm', 'Bb', 'Bb', 'C', 'C', 'Am', 'Am'];
const CAVE_MEL = `
  D5:4 -:2 F5:2 | E5:6 -:2 | C5:3 D5:1 E5:2 G5:2 | A4:8 |
  D5:2 F5:2 A5:4 | G5:4 F5:2 E5:2 | D5:6 C5:2 | D5:8`;
const TOWER_CH = ['Cm', 'Ab', 'Bb', 'G', 'Cm', 'Ab', 'Bb', 'G'];
const TOWER_MEL = `
  C5:4 Eb5:2 G5:2 | F5:4 Eb5:2 D5:2 | Eb5:3 D5:1 C5:2 Bb4:2 | B4:8 |
  C5:2 G5:2 C6:4 | Bb5:4 Ab5:2 G5:2 | F5:2 Eb5:2 D5:2 F5:2 | G5:8`;

// ---- 第二部：竜の背と五つの島
const FLIGHT_CH = ['D', 'A', 'Bm', 'G', 'D', 'A', 'G', 'A', 'Bm', 'F#m', 'G', 'D', 'Em', 'A', 'D', 'D'];
const FLIGHT_MEL = `
  A4:2 D5:2 F#5:3 E5:1 | E5:2 C#5:2 A4:4 | B4:2 D5:2 F#5:2 A5:2 | G5:6 -:2 |
  F#5:2 A5:2 D6:3 C#6:1 | B5:2 A5:2 E5:4 | G5:2 F#5:2 E5:2 D5:2 | E5:6 -:2 |
  D5:2 F#5:2 B5:4 | A5:2 F#5:2 C#5:4 | D5:2 E5:2 G5:2 B5:2 | A5:6 F#5:2 |
  G5:3 F#5:1 E5:2 G5:2 | F#5:3 E5:1 D5:2 F#5:2 | E5:2 D5:2 C#5:2 E5:2 | D5:8`;
const DESERT_CH = ['Am', 'Am', 'Dm', 'E', 'Am', 'F', 'E', 'E', 'Dm', 'Am', 'E', 'Am', 'F', 'E', 'Am', 'E'];
const DESERT_MEL = `
  A4:2 B4:1 C5:1 E5:3 D5:1 | C5:2 B4:2 A4:4 | D5:2 F5:2 E5:2 D5:2 | G#4:6 -:2 |
  A4:2 C5:2 E5:2 A5:2 | G5:1 F5:1 E5:2 F5:4 | E5:2 D5:2 C5:2 B4:2 | G#4:4 B4:4 |
  F5:3 E5:1 D5:2 F5:2 | E5:2 C5:2 A4:4 | B4:2 C5:2 D5:2 G#4:2 | A4:6 -:2 |
  F5:2 E5:2 D5:2 C5:2 | B4:2 C5:1 B4:1 G#4:4 | A4:2 C5:2 E5:2 F5:2 | E5:8`;
const ICE_CH = ['Em', 'C', 'G', 'D', 'Em', 'C', 'B', 'B', 'Am', 'Em', 'C', 'G', 'Am', 'B', 'Em', 'Em'];
const ICE_MEL = `
  B4:2 E5:2 G5:4 | E5:2 C5:2 E5:4 | D5:2 G5:2 B5:4 | A5:4 F#5:4 |
  G5:3 F#5:1 E5:2 B4:2 | C5:2 E5:2 G5:4 | F#5:2 D#5:2 B4:4 | -:8 |
  A4:2 C5:2 E5:4 | G5:2 E5:2 B4:4 | C5:2 E5:2 G5:2 C6:2 | B5:6 -:2 |
  A5:2 G5:2 F#5:2 E5:2 | D#5:2 F#5:2 B4:4 | E5:2 G5:2 B5:4 | E5:8`;
const VOLC_CH = ['Cm', 'Cm', 'Ab', 'Bb', 'Cm', 'Cm', 'Fm', 'G', 'Ab', 'Bb', 'Cm', 'Ab', 'Fm', 'G', 'Cm', 'G'];
const VOLC_MEL = `
  C5:1 C5:1 Eb5:2 G5:2 C6:2 | Bb5:2 G5:2 F5:2 Eb5:2 | Ab5:3 G5:1 F5:2 Eb5:2 | D5:4 F5:4 |
  G5:1 G5:1 C6:2 Bb5:2 G5:2 | Ab5:2 G5:2 F5:2 Eb5:2 | F5:2 Ab5:2 C6:2 Ab5:2 | B5:4 G5:4 |
  C6:2 Bb5:2 Ab5:2 Eb5:2 | D5:2 F5:2 Bb5:4 | G5:2 Eb5:2 C5:2 Eb5:2 | Ab5:6 -:2 |
  F5:2 Ab5:2 C6:2 F6:2 | D6:2 B5:2 G5:4 | C6:3 G5:1 Eb5:2 C5:2 | D5:4 B4:4`;
const DARK_CH = ['Dm', 'Bb', 'Gm', 'A', 'Dm', 'Bb', 'E', 'A', 'Gm', 'Dm', 'Bb', 'A', 'Dm', 'Gm', 'A', 'Dm'];
const DARK_MEL = `
  D5:4 C#5:2 D5:2 | F5:4 E5:2 D5:2 | Bb4:3 A4:1 G4:2 Bb4:2 | A4:8 |
  D5:2 F5:2 A5:4 | G#5:4 F5:2 E5:2 | E5:3 F5:1 G#5:2 B5:2 | A5:8 |
  Bb5:4 A5:2 G5:2 | F5:4 E5:2 D5:2 | F5:2 E5:2 D5:2 Bb4:2 | C#5:6 -:2 |
  D5:3 E5:1 F5:2 A5:2 | Bb5:3 A5:1 G5:2 E5:2 | C#5:2 E5:2 A5:4 | D5:8`;
const BOSS2_CH = ['Em', 'Em', 'C', 'D', 'Em', 'Em', 'C', 'B', 'Am', 'B', 'Em', 'C', 'Am', 'B', 'Em', 'B'];
const BOSS2_MEL = `
  E5:1 G5:1 B5:2 E6:2 D6:1 B5:1 | C6:2 B5:2 A5:2 G5:2 | A5:1 B5:1 C6:2 B5:2 A5:2 | F#5:4 D5:4 |
  E5:1 G5:1 B5:2 E6:2 F#6:2 | G6:2 F#6:2 E6:2 C6:2 | B5:2 A5:2 G5:2 F#5:2 | D#5:4 F#5:4 |
  A5:2 C6:2 E6:2 C6:2 | B5:2 D#6:2 F#6:4 | E6:2 B5:2 G5:2 B5:2 | C6:2 E6:2 G6:4 |
  F#6:2 E6:2 C6:2 A5:2 | B5:2 A5:2 F#5:2 D#5:2 | E5:2 G5:2 B5:2 E6:2 | D#6:4 B5:4`;
const FINAL_CH = ['Cm', 'Ab', 'Fm', 'G', 'Cm', 'Ab', 'Db', 'G', 'Fm', 'Cm', 'Ab', 'G', 'Fm', 'Db', 'G', 'G'];
const FINAL_MEL = `
  C5:2 Eb5:2 G5:2 C6:2 | Ab5:3 G5:1 F5:2 Eb5:2 | F5:2 Ab5:2 C6:2 Eb6:2 | D6:4 B5:4 |
  C6:2 G5:2 Eb5:2 C5:2 | Ab5:2 C6:2 Eb6:4 | Db6:3 C6:1 Bb5:2 Ab5:2 | B5:6 -:2 |
  Ab5:2 C6:2 F6:2 C6:2 | G5:2 C6:2 Eb6:4 | Eb6:2 D6:2 C6:2 Ab5:2 | G5:6 -:2 |
  F5:2 Ab5:2 C6:2 F6:2 | Db6:2 F6:2 Ab6:4 | G6:4 F6:2 D6:2 | B5:4 G5:4`;
const down = (mel) => mel.replace(/([A-G][#b]?)(\d)/g, (m, n, o) => n + (parseInt(o, 10) - 1));

const SONGS = {
  flight: {
    bpm: 120, tracks: [
      { inst: 'brass', vol: 0.12, s: FLIGHT_MEL },
      { inst: 'strings', vol: 0.08, s: padLine(FLIGHT_CH, 8, 1) },
      { inst: 'bass', vol: 0.28, s: bassLine(FLIGHT_CH, [[0, 2, -1], [2, 2, -1], [0, 2, 0], [1, 2, -1]]) },
      { inst: 'bell', vol: 0.04, s: arpLine(FLIGHT_CH, [[0, 1], [1, 1], [2, 1], [1, 1], [0, 1], [1, 1], [2, 1], [1, 1]], 2) },
      { inst: 'drum', vol: 0.2, s: rep('k:2 h:1 h:1 s:2 h:1 o:1', 16) },
    ],
  },
  desert: {
    bpm: 96, tracks: [
      { inst: 'flute', vol: 0.15, s: DESERT_MEL },
      { inst: 'bass', vol: 0.27, s: bassLine(DESERT_CH, [[0, 3, -1], [0, 1, -1], [2, 2, -1], [0, 2, 0]]) },
      { inst: 'pad', vol: 0.06, s: padLine(DESERT_CH, 8) },
      { inst: 'drum', vol: 0.2, s: rep('k:2 h:1 k:1 s:2 h:1 h:1', 16) },
    ],
  },
  ruins: {
    bpm: 72, tracks: [
      { inst: 'bell', vol: 0.11, s: DESERT_MEL },
      { inst: 'pad', vol: 0.08, s: padLine(DESERT_CH, 8) },
      { inst: 'bass', vol: 0.22, s: bassLine(DESERT_CH, [[0, 8, -1]]) },
    ],
  },
  ice: {
    bpm: 78, tracks: [
      { inst: 'bell', vol: 0.13, s: ICE_MEL },
      { inst: 'strings', vol: 0.07, s: padLine(ICE_CH, 8, 1) },
      { inst: 'bass', vol: 0.22, s: bassLine(ICE_CH, [[0, 4, -1], [2, 4, -1]]) },
      { inst: 'flute', vol: 0.05, s: arpLine(ICE_CH, [[0, 2], [1, 2], [2, 2], [1, 2]], 2) },
    ],
  },
  icecave: {
    bpm: 62, tracks: [
      { inst: 'bell', vol: 0.1, s: ICE_MEL },
      { inst: 'pad', vol: 0.09, s: padLine(ICE_CH, 8) },
      { inst: 'bass', vol: 0.2, s: bassLine(ICE_CH, [[0, 8, -1]]) },
    ],
  },
  volcano: {
    bpm: 138, tracks: [
      { inst: 'lead', vol: 0.13, s: VOLC_MEL },
      { inst: 'bass', vol: 0.3, s: bassLine(VOLC_CH, [[0, 1, -1], [0, 1, -1], [0, 1, 0], [0, 1, -1], [2, 1, -1], [0, 1, -1], [0, 1, 0], [1, 1, -1]]) },
      { inst: 'organ', vol: 0.06, s: padLine(VOLC_CH, 8, 1) },
      { inst: 'drum', vol: 0.24, s: rep('k:1 h:1 s:1 h:1 k:1 k:1 s:1 h:1', 16) },
    ],
  },
  lavacave: {
    bpm: 104, tracks: [
      { inst: 'organ', vol: 0.1, s: VOLC_MEL },
      { inst: 'bass', vol: 0.28, s: bassLine(VOLC_CH, [[0, 2, -1], [0, 2, -1], [2, 2, -1], [0, 2, -1]]) },
      { inst: 'drum', vol: 0.2, s: rep('k:4 -:2 k:1 k:1', 16) },
    ],
  },
  dark: {
    bpm: 74, tracks: [
      { inst: 'strings', vol: 0.11, s: DARK_MEL },
      { inst: 'organ', vol: 0.07, s: padLine(DARK_CH, 8, 1) },
      { inst: 'bass', vol: 0.26, s: bassLine(DARK_CH, [[0, 4, -1], [0, 4, -2]]) },
      { inst: 'bell', vol: 0.04, s: '-:6 D6:1 -:9 A5:1 -:15 F6:1 -:12 C#6:1 -:19' },
    ],
  },
  darkcastle: {
    bpm: 88, tracks: [
      { inst: 'organ', vol: 0.1, s: DARK_MEL },
      { inst: 'brass', vol: 0.05, s: down(DARK_MEL) },
      { inst: 'bass', vol: 0.28, s: bassLine(DARK_CH, [[0, 2, -1], [0, 2, -1], [2, 2, -1], [0, 2, -1]]) },
      { inst: 'drum', vol: 0.18, s: rep('k:4 -:2 s:1 s:1', 16) },
    ],
  },
  boss2: {
    bpm: 158, tracks: [
      { inst: 'brass', vol: 0.12, s: BOSS2_MEL },
      { inst: 'lead', vol: 0.06, s: down(BOSS2_MEL) },
      { inst: 'bass', vol: 0.32, s: bassLine(BOSS2_CH, [[0, 1, -1], [0, 1, -1], [0, 1, 0], [0, 1, -1], [1, 1, -1], [0, 1, -1], [0, 1, 0], [2, 1, -1]]) },
      { inst: 'strings', vol: 0.06, s: padLine(BOSS2_CH, 8, 1) },
      { inst: 'drum', vol: 0.28, s: 'c:2 s:1 s:1 k:1 k:1 s:1 h:1 ' + rep('k:1 h:1 s:1 k:1 k:1 h:1 s:1 o:1', 15) },
    ],
  },
  final: {
    bpm: 146, tracks: [
      { inst: 'organ', vol: 0.1, s: FINAL_MEL },
      { inst: 'brass', vol: 0.09, s: down(FINAL_MEL) },
      { inst: 'bass', vol: 0.34, s: bassLine(FINAL_CH, [[0, 1, -1], [0, 1, -1], [0, 1, 0], [0, 1, -1], [1, 1, -1], [0, 1, -1], [2, 1, 0], [0, 1, -1]]) },
      { inst: 'strings', vol: 0.07, s: padLine(FINAL_CH, 8, 1) },
      { inst: 'drum', vol: 0.3, s: 'c:2 s:1 s:1 k:1 k:1 s:1 s:1 ' + rep('k:1 h:1 s:1 k:1 k:1 h:1 s:1 s:1', 15) },
    ],
  },
  cave: {
    bpm: 68, tracks: [
      { inst: 'bell', vol: 0.1, s: CAVE_MEL },
      { inst: 'pad', vol: 0.08, s: padLine(CAVE_CH, 8) },
      { inst: 'bass', vol: 0.24, s: bassLine(CAVE_CH, [[0, 8, -1]]) },
      { inst: 'bell', vol: 0.05, s: '-:5 D6:1 -:10 A5:1 -:7 F6:1 -:8 -:4 E6:1 -:12 C6:1 -:13' },
    ],
  },
  tower: {
    bpm: 92, tracks: [
      { inst: 'brass', vol: 0.1, s: TOWER_MEL },
      { inst: 'organ', vol: 0.07, s: padLine(TOWER_CH, 8) },
      { inst: 'bass', vol: 0.28, s: bassLine(TOWER_CH, [[0, 2, -1], [0, 2, -1], [2, 2, -1], [0, 2, -1]]) },
      { inst: 'drum', vol: 0.2, s: rep('k:4 -:2 k:1 k:1', 8) },
    ],
  },
  field: {
    bpm: 112, tracks: [
      { inst: 'lead', vol: 0.16, s: FIELD_MEL },
      { inst: 'bass', vol: 0.30, s: bassLine(FIELD_CH, [[0, 2, -1], [2, 2, -1], [0, 2, 0], [2, 2, -1]]) },
      { inst: 'pad', vol: 0.07, s: padLine(FIELD_CH, 8) },
      { inst: 'bell', vol: 0.05, s: arpLine(FIELD_CH, [[0, 1], [1, 1], [2, 1], [1, 1], [0, 1], [1, 1], [2, 1], [1, 1]], 2) },
      { inst: 'drum', vol: 0.22, s: rep('k:2 h:1 h:1 s:2 h:1 h:1', 16) },
    ],
  },
  field_night: {
    bpm: 84, tracks: [
      { inst: 'bell', vol: 0.12, s: FIELD_MEL },
      { inst: 'bass', vol: 0.22, s: bassLine(FIELD_CH, [[0, 4, -1], [2, 4, -1]]) },
      { inst: 'pad', vol: 0.09, s: padLine(FIELD_CH, 8) },
    ],
  },
  town: {
    bpm: 100, tracks: [
      { inst: 'flute', vol: 0.15, s: TOWN_MEL },
      { inst: 'bass', vol: 0.26, s: bassLine(TOWN_CH, [[0, 2, -1], [1, 2, 0], [2, 2, 0]]) + ' | ' + bassLine(TOWN_CH, [[0, 2, -1], [1, 2, 0], [2, 2, 0]]) },
      { inst: 'bell', vol: 0.05, s: arpLine(TOWN_CH, [[-0 + 2, 2], [1, 2], [2, 2]], 2) + ' ' + arpLine(TOWN_CH, [[2, 2], [1, 2], [2, 2]], 2) },
      { inst: 'pad', vol: 0.06, s: padLine(TOWN_CH, 6) + ' ' + padLine(TOWN_CH, 6) },
    ],
  },
  castle: {
    bpm: 80, tracks: [
      { inst: 'brass', vol: 0.12, s: CASTLE_MEL },
      { inst: 'strings', vol: 0.09, s: padLine(CASTLE_CH, 8, 1) },
      { inst: 'bass', vol: 0.26, s: bassLine(CASTLE_CH, [[0, 4, -1], [0, 4, -2]]) },
      { inst: 'drum', vol: 0.16, s: rep('k:4 -:2 s:1 s:1', 16) },
    ],
  },
  battle: {
    bpm: 164, tracks: [
      { inst: 'lead', vol: 0.15, s: BATTLE_MEL },
      { inst: 'bass', vol: 0.30, s: bassLine(BATTLE_CH, [[0, 1, -1], [0, 1, 0], [0, 1, -1], [0, 1, 0], [0, 1, -1], [0, 1, 0], [2, 1, -1], [0, 1, 0]]) },
      { inst: 'strings', vol: 0.06, s: padLine(BATTLE_CH, 8, 1) },
      { inst: 'drum', vol: 0.26, s: 'c:1 h:1 s:1 h:1 k:1 k:1 s:1 h:1 ' + rep('k:1 h:1 s:1 h:1 k:1 k:1 s:1 o:1', 15) },
    ],
  },
  boss: {
    bpm: 150, tracks: [
      { inst: 'brass', vol: 0.13, s: BOSS_MEL },
      { inst: 'lead', vol: 0.06, s: BOSS_MEL.replace(/([A-G][#b]?)(\d)/g, (m, n, o) => n + (parseInt(o, 10) - 1)) },
      { inst: 'bass', vol: 0.32, s: bassLine(BOSS_CH, [[0, 1, -1], [0, 1, -1], [0, 1, 0], [0, 1, -1], [1, 1, -1], [0, 1, -1], [0, 1, 0], [2, 1, -1]]) },
      { inst: 'organ', vol: 0.06, s: padLine(BOSS_CH, 8, 1) },
      { inst: 'drum', vol: 0.28, s: 'c:2 s:1 s:1 k:1 k:1 s:1 h:1 ' + rep('k:1 h:1 s:1 k:1 k:1 h:1 s:1 s:1', 15) },
    ],
  },
  victory: {
    bpm: 132, loop: false, tracks: [
      { inst: 'brass', vol: 0.15, s: 'G4:1 C5:1 E5:1 G5:3 E5:1 G5:1 | C6:6 -:2 | A5:1 B5:1 C6:1 D6:3 B5:2 | C6:8' },
      { inst: 'strings', vol: 0.08, s: 'C4+E4+G4:8 F4+A4+C5:4 G4+B4+D5:4 C4+E4+G4+C5:8' },
      { inst: 'drum', vol: 0.2, s: 'c:1 s:1 s:1 k:3 s:1 s:1 c:6 -:2 k:1 k:1 s:1 k:3 s:2 c:8' },
    ],
  },
  levelup: {
    bpm: 150, loop: false, tracks: [
      { inst: 'bell', vol: 0.18, s: 'C5:1 E5:1 G5:1 C6:1 E6:1 G6:1 C7:4' },
      { inst: 'lead', vol: 0.1, s: '-:3 G5:1 C6:2 E6:4' },
    ],
  },
  inn: {
    bpm: 70, loop: false, tracks: [
      { inst: 'bell', vol: 0.15, s: 'E5:2 G5:2 C6:4 | B5:2 G5:2 D5:4 | F5:2 A5:2 E5:2 C5:2 | C5:8' },
      { inst: 'pad', vol: 0.08, s: 'C4+E4+G4:8 G3+B3+D4:8 F3+A3+C4:8 C4+E4+G4:8' },
    ],
  },
  gameover: {
    bpm: 60, loop: false, tracks: [
      { inst: 'strings', vol: 0.12, s: 'A4:3 G4:1 E4:4 | F4:3 E4:1 D4:4 | C4:2 D4:2 E4:2 G#4:2 | A4:8' },
      { inst: 'bass', vol: 0.22, s: 'A2:8 D2:8 E2:8 A2:8' },
    ],
  },
  title: null,
  ending: null,
};
SONGS.title = SONGS.castle;
SONGS.ending = { ...SONGS.castle, bpm: 72 };

export class Audio {
  constructor() {
    this.ctx = null;
    this.current = null;
    this.musicVol = 0.8;
    this.sfxVol = 0.9;
  }

  unlock() {
    if (this.ctx) { if (this.ctx.state === 'suspended') this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = new AC();
    this.ctx = ctx;
    this.master = ctx.createGain();
    this.master.gain.value = 0.9;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -14; comp.ratio.value = 3;
    this.master.connect(comp).connect(ctx.destination);
    this.music = ctx.createGain();
    this.music.gain.value = this.musicVol;
    this.sfxBus = ctx.createGain();
    this.sfxBus.gain.value = this.sfxVol;
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this.impulse(2.6, 2.4);
    this.revSend = ctx.createGain();
    this.revSend.gain.value = 0.32;
    this.music.connect(this.master);
    this.music.connect(this.revSend);
    this.sfxBus.connect(this.master);
    this.revSend.connect(this.reverb).connect(this.master);
    this.noiseBuf = this.makeNoise();
    if (this.pending) { const p = this.pending; this.pending = null; this.play(p); }
  }

  impulse(sec, decay) {
    const ctx = this.ctx, len = Math.floor(ctx.sampleRate * sec);
    const b = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = b.getChannelData(c);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
    }
    return b;
  }

  makeNoise() {
    const ctx = this.ctx, len = ctx.sampleRate;
    const b = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = b.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    return b;
  }

  // ------------------------------------------------------------ BGM
  play(name, { fade = 0.6 } = {}) {
    if (!this.ctx) { this.pending = name; return; }
    if (this.current && this.current.name === name) return;
    this.stop(fade);
    const song = SONGS[name];
    if (!song) return;
    const spb = 60 / song.bpm / 2; // 8分音符の秒数
    const tracks = song.tracks.map((t) => ({ ...t, ...parse(t.s) }));
    const length = Math.max(...tracks.map((t) => t.length));
    const bus = this.ctx.createGain();
    bus.gain.setValueAtTime(0, this.ctx.currentTime);
    bus.gain.linearRampToValueAtTime(1, this.ctx.currentTime + 0.3);
    bus.connect(this.music);
    const cur = { name, song, tracks, length, spb, bus, start: this.ctx.currentTime + 0.08, loop: song.loop !== false, idx: tracks.map(() => 0), iter: 0 };
    this.current = cur;
    cur.timer = setInterval(() => this.schedule(cur), 40);
    this.schedule(cur);
  }

  stop(fade = 0.5) {
    const cur = this.current;
    if (!cur) return;
    clearInterval(cur.timer);
    const t = this.ctx.currentTime;
    cur.bus.gain.cancelScheduledValues(t);
    cur.bus.gain.setValueAtTime(cur.bus.gain.value, t);
    cur.bus.gain.linearRampToValueAtTime(0, t + fade);
    setTimeout(() => cur.bus.disconnect(), (fade + 0.2) * 1000);
    this.current = null;
  }

  schedule(cur) {
    const ahead = this.ctx.currentTime + 0.25;
    for (;;) {
      let any = false;
      cur.tracks.forEach((tr, ti) => {
        while (cur.idx[ti] < tr.events.length) {
          const ev = tr.events[cur.idx[ti]];
          const when = cur.start + (cur.iter * cur.length + ev.t) * cur.spb;
          if (when > ahead) break;
          if (when >= this.ctx.currentTime - 0.05) this.note(tr.inst, ev.notes, when, ev.len * cur.spb, tr.vol, cur.bus);
          cur.idx[ti]++;
          any = true;
        }
      });
      const allDone = cur.tracks.every((tr, ti) => cur.idx[ti] >= tr.events.length);
      const endTime = cur.start + (cur.iter + 1) * cur.length * cur.spb;
      if (allDone && endTime - 0.05 < ahead) {
        if (!cur.loop) { clearInterval(cur.timer); if (cur.onEnd) setTimeout(cur.onEnd, (endTime - this.ctx.currentTime) * 1000); return; }
        cur.iter++;
        cur.idx = cur.tracks.map(() => 0);
        continue;
      }
      if (!any) break;
    }
  }

  /** ジングルを鳴らして終わったら元の曲に戻す */
  jingle(name, resume) {
    if (!this.ctx) return Promise.resolve();
    const prev = resume ?? (this.current && this.current.name);
    return new Promise((res) => {
      this.play(name, { fade: 0.15 });
      const cur = this.current;
      if (!cur) return res();
      cur.onEnd = () => { if (this.current === cur) { this.current = null; if (prev) this.play(prev); } res(); };
    });
  }

  // ------------------------------------------------------------ 楽器
  env(g, t, dur, a, d, s, r, peak) {
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(peak, t + a);
    g.gain.linearRampToValueAtTime(peak * s, t + a + d);
    g.gain.setValueAtTime(peak * s, t + Math.max(a + d, dur));
    g.gain.linearRampToValueAtTime(0.0001, t + Math.max(a + d, dur) + r);
    return t + Math.max(a + d, dur) + r;
  }

  note(inst, notes, t, dur, vol, out) {
    const ctx = this.ctx;
    if (inst === 'drum') { for (const n of notes) this.drum(n, t, vol, out); return; }
    for (const n of notes) {
      const f = freq(n);
      if (!f) continue;
      const g = ctx.createGain();
      let end;
      const oscs = [];
      const mk = (type, fr, det = 0) => { const o = ctx.createOscillator(); o.type = type; o.frequency.value = fr; o.detune.value = det; oscs.push(o); return o; };
      const filt = ctx.createBiquadFilter();
      filt.type = 'lowpass';
      if (inst === 'lead') {
        mk('square', f, -6).connect(filt); mk('square', f, 6).connect(filt);
        filt.frequency.value = 3200; filt.Q.value = 0.5;
        const lfo = ctx.createOscillator(), lg = ctx.createGain();
        lfo.frequency.value = 5.5; lg.gain.setValueAtTime(0, t); lg.gain.linearRampToValueAtTime(9, t + Math.min(dur, 0.4));
        lfo.connect(lg); oscs.forEach((o) => lg.connect(o.detune)); oscs.push(lfo);
        end = this.env(g, t, dur * 0.92, 0.01, 0.08, 0.75, 0.08, vol * 0.5);
      } else if (inst === 'flute') {
        mk('triangle', f).connect(filt); mk('sine', f * 2, 3).connect(filt);
        filt.frequency.value = 4000;
        const lfo = ctx.createOscillator(), lg = ctx.createGain();
        lfo.frequency.value = 5; lg.gain.value = 7; lfo.connect(lg); oscs.forEach((o) => lg.connect(o.detune)); oscs.push(lfo);
        end = this.env(g, t, dur * 0.95, 0.04, 0.1, 0.8, 0.12, vol * 0.9);
      } else if (inst === 'bass') {
        mk('triangle', f).connect(filt); mk('sine', f / 2).connect(filt);
        filt.frequency.value = 900;
        end = this.env(g, t, dur * 0.85, 0.005, 0.12, 0.6, 0.05, vol);
      } else if (inst === 'pad' || inst === 'strings' || inst === 'organ') {
        const type = inst === 'organ' ? 'square' : 'sawtooth';
        mk(type, f, -9).connect(filt); mk(type, f, 9).connect(filt); if (inst === 'strings') mk('sawtooth', f * 2, 4).connect(filt);
        filt.frequency.value = inst === 'organ' ? 1400 : 1800; filt.Q.value = 0.3;
        end = this.env(g, t, dur, inst === 'strings' ? 0.18 : 0.35, 0.3, 0.8, 0.5, vol * 0.5);
      } else if (inst === 'brass') {
        mk('sawtooth', f, -4).connect(filt); mk('sawtooth', f, 4).connect(filt);
        filt.Q.value = 1.2;
        filt.frequency.setValueAtTime(400, t);
        filt.frequency.linearRampToValueAtTime(3200, t + 0.06);
        filt.frequency.linearRampToValueAtTime(1800, t + 0.3);
        end = this.env(g, t, dur * 0.95, 0.02, 0.1, 0.8, 0.1, vol * 0.6);
      } else { // bell（FM）
        const car = mk('sine', f);
        const mod = ctx.createOscillator(), mg = ctx.createGain();
        mod.frequency.value = f * 3.5; mg.gain.setValueAtTime(f * 1.4, t); mg.gain.exponentialRampToValueAtTime(f * 0.05, t + 0.8);
        mod.connect(mg).connect(car.frequency); oscs.push(mod);
        car.connect(filt); filt.frequency.value = 6000;
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + 0.005);
        g.gain.exponentialRampToValueAtTime(0.0001, t + Math.max(1.2, dur * 1.5));
        end = t + Math.max(1.2, dur * 1.5);
      }
      filt.connect(g).connect(out);
      oscs.forEach((o) => { o.start(t); o.stop(end + 0.05); });
    }
  }

  drum(n, t, vol, out) {
    const ctx = this.ctx;
    const g = ctx.createGain();
    g.connect(out);
    if (n === 'k') {
      const o = ctx.createOscillator();
      o.frequency.setValueAtTime(150, t); o.frequency.exponentialRampToValueAtTime(42, t + 0.12);
      g.gain.setValueAtTime(vol * 1.4, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.22);
      o.connect(g); o.start(t); o.stop(t + 0.25);
    } else {
      const s = ctx.createBufferSource(); s.buffer = this.noiseBuf;
      const f = ctx.createBiquadFilter();
      let len = 0.05;
      if (n === 's') { f.type = 'bandpass'; f.frequency.value = 1800; f.Q.value = 0.7; len = 0.16; g.gain.setValueAtTime(vol * 0.9, t); }
      else if (n === 'h') { f.type = 'highpass'; f.frequency.value = 7000; len = 0.04; g.gain.setValueAtTime(vol * 0.35, t); }
      else if (n === 'o') { f.type = 'highpass'; f.frequency.value = 6000; len = 0.2; g.gain.setValueAtTime(vol * 0.3, t); }
      else { f.type = 'highpass'; f.frequency.value = 3000; len = 1.2; g.gain.setValueAtTime(vol * 0.5, t); }
      g.gain.exponentialRampToValueAtTime(0.001, t + len);
      s.connect(f).connect(g); s.start(t, Math.random() * 0.5); s.stop(t + len + 0.05);
      if (n === 's') {
        const o = ctx.createOscillator(), og = ctx.createGain();
        o.frequency.setValueAtTime(220, t); o.frequency.exponentialRampToValueAtTime(140, t + 0.08);
        og.gain.setValueAtTime(vol * 0.5, t); og.gain.exponentialRampToValueAtTime(0.001, t + 0.1);
        o.connect(og).connect(out); o.start(t); o.stop(t + 0.12);
      }
    }
  }

  // ------------------------------------------------------------ 効果音
  tone(type, f0, f1, dur, vol, t0 = 0, out) {
    const ctx = this.ctx, t = ctx.currentTime + t0;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    if (f1 !== f0) o.frequency.exponentialRampToValueAtTime(Math.max(f1, 1), t + dur);
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.0008, t + dur);
    o.connect(g).connect(out || this.sfxBus);
    o.start(t); o.stop(t + dur + 0.02);
  }
  noise(dur, vol, type, f0, f1, t0 = 0, q = 0.8) {
    const ctx = this.ctx, t = ctx.currentTime + t0;
    const s = ctx.createBufferSource(); s.buffer = this.noiseBuf;
    const f = ctx.createBiquadFilter(); f.type = type; f.Q.value = q;
    f.frequency.setValueAtTime(f0, t); f.frequency.exponentialRampToValueAtTime(f1, t + dur);
    const g = ctx.createGain(); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0008, t + dur);
    s.connect(f).connect(g).connect(this.sfxBus);
    s.start(t, Math.random() * 0.4); s.stop(t + dur + 0.02);
  }

  sfx(name) {
    if (!this.ctx) return;
    switch (name) {
      case 'cursor': this.tone('square', 1320, 1320, 0.035, 0.05); break;
      case 'confirm': this.tone('square', 990, 990, 0.04, 0.06); this.tone('square', 1480, 1480, 0.06, 0.06, 0.045); break;
      case 'cancel': this.tone('square', 700, 420, 0.08, 0.06); break;
      case 'text': this.tone('square', 1500, 1500, 0.012, 0.012); break;
      case 'step': this.noise(0.05, 0.035, 'lowpass', 900, 300); break;
      case 'swing': this.noise(0.22, 0.25, 'bandpass', 600, 3800, 0, 1.5); break;
      case 'hit': this.noise(0.18, 0.5, 'lowpass', 3000, 200); this.tone('square', 180, 60, 0.12, 0.25); break;
      case 'crit': this.noise(0.3, 0.6, 'lowpass', 5000, 200); this.tone('square', 240, 50, 0.2, 0.3); this.tone('triangle', 1760, 1760, 0.4, 0.12, 0.02); break;
      case 'hurt': this.tone('sawtooth', 220, 70, 0.25, 0.25); this.noise(0.2, 0.35, 'lowpass', 1200, 100); break;
      case 'miss': this.noise(0.18, 0.12, 'highpass', 2000, 6000); break;
      case 'spell': for (let i = 0; i < 6; i++) this.tone('sine', 600 + i * 220, 900 + i * 260, 0.25, 0.06, i * 0.05); break;
      case 'fire': this.noise(0.8, 0.5, 'bandpass', 300, 2400, 0, 0.6); this.noise(0.6, 0.25, 'lowpass', 900, 120, 0.15); break;
      case 'thunder': this.noise(0.08, 0.7, 'highpass', 4000, 3000); this.noise(1.4, 0.7, 'lowpass', 1600, 60, 0.05); break;
      case 'storm': for (let i = 0; i < 4; i++) this.noise(0.6, 0.4, 'bandpass', 250 + i * 150, 2500, i * 0.18, 0.7); break;
      case 'light': for (let i = 0; i < 8; i++) this.tone('triangle', 880 * Math.pow(1.122, i), 880 * Math.pow(1.122, i), 0.5, 0.06, i * 0.04); this.noise(1.0, 0.4, 'bandpass', 800, 5000, 0.3); break;
      case 'heal': [523, 659, 784, 1047, 1319].forEach((f, i) => this.tone('sine', f, f, 0.4, 0.09, i * 0.06)); break;
      case 'item': [784, 988, 1175].forEach((f, i) => this.tone('square', f, f, 0.1, 0.05, i * 0.08)); break;
      case 'save': [659, 784, 1047, 1319].forEach((f, i) => this.tone('triangle', f, f, 0.25, 0.08, i * 0.1)); break;
      case 'encounter': this.noise(0.6, 0.35, 'bandpass', 200, 4000, 0, 2); [880, 660, 880, 660, 1320].forEach((f, i) => this.tone('square', f, f, 0.07, 0.07, i * 0.07)); break;
      case 'kill': this.noise(0.5, 0.3, 'bandpass', 3000, 200, 0, 1); this.tone('square', 600, 80, 0.4, 0.1); break;
      case 'flee': [600, 500, 400, 300].forEach((f, i) => this.tone('square', f, f, 0.05, 0.06, i * 0.06)); break;
      case 'roar': this.tone('sawtooth', 120, 45, 1.4, 0.35); this.noise(1.3, 0.5, 'lowpass', 900, 80); break;
      case 'breath': this.noise(1.6, 0.6, 'bandpass', 200, 1800, 0, 0.5); this.tone('sawtooth', 90, 40, 1.5, 0.2); break;
      case 'door': this.noise(0.3, 0.2, 'lowpass', 600, 100); break;
      case 'coin': this.tone('square', 1976, 1976, 0.06, 0.05); this.tone('square', 2637, 2637, 0.25, 0.05, 0.06); break;
      default: break;
    }
  }
}
