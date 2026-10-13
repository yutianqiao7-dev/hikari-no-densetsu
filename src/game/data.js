export const MONSTERS = {
  purun: { name: 'ぷるりん', model: 'Mon_Purun', scale: 1.1, hp: 8, atk: 9, def: 3, agi: 5, exp: 2, gold: 3 },
  mushroom: { name: 'おばけキノコ', model: 'Mon_Mushroom', scale: 1.15, hp: 13, atk: 12, def: 6, agi: 3, exp: 4, gold: 5, skill: 'spore' },
  bat: { name: 'コウモリン', model: 'Mon_Bat', scale: 1.0, hp: 15, atk: 15, def: 7, agi: 15, exp: 6, gold: 6, skill: 'drain' },
  purun_red: { name: 'ベニぷるりん', model: 'Mon_Purun', scale: 1.25, recolor: { Gel: '#ff5a48', SproutLeaf: '#3a8a2a' }, hp: 20, atk: 17, def: 9, agi: 9, exp: 9, gold: 10 },
  ghost: { name: 'さまようゴースト', model: 'Mon_Ghost', scale: 1.0, hp: 24, atk: 19, def: 11, agi: 13, exp: 13, gold: 14, skill: 'fire' },
  mushroom_poison: { name: 'ドクキノコ', model: 'Mon_Mushroom', scale: 1.35, recolor: { Cap: '#8a3de0', Stem: '#e4dcff', Gill: '#c9b8f0' }, hp: 34, atk: 27, def: 17, agi: 8, exp: 22, gold: 20, skill: 'spore' },
  bat_dark: { name: 'ヤミコウモリン', model: 'Mon_Bat', scale: 1.25, recolor: { BatFur: '#2c2536', BatBelly: '#6e5f74', BatWing: '#4a1218', BatEarIn: '#a03040' }, hp: 32, atk: 30, def: 16, agi: 22, exp: 24, gold: 22, skill: 'drain' },
  golem: { name: 'いわゴーレム', model: 'Mon_Golem', scale: 1.0, hp: 70, atk: 38, def: 32, agi: 4, exp: 48, gold: 42, skill: 'smash' },
  ghost_blue: { name: 'ゆらめきの霊', model: 'Mon_Ghost', scale: 1.3, recolor: { Ghost: '#8fd0ff', GhostSkirt: '#8fd0ff' }, hp: 48, atk: 34, def: 22, agi: 26, exp: 40, gold: 36, skill: 'fire' },
  // ---- 森・草原
  stump: { name: 'キリカブー', model: 'Mon_Stump', scale: 1.0, hp: 12, atk: 11, def: 7, agi: 3, exp: 4, gold: 6, skill: 'strike', skillText: 'は えだを むちのように しならせた！', skillMul: 1.3 },
  snake: { name: 'アオコブラ', model: 'Mon_Snake', scale: 1.0, hp: 16, atk: 14, def: 6, agi: 12, exp: 6, gold: 7, skill: 'strike', skillText: 'は するどい きばで かみついた！', skillMul: 1.4 },
  wolf: { name: 'キバウルフ', model: 'Mon_Wolf', scale: 1.0, hp: 26, atk: 20, def: 9, agi: 18, exp: 11, gold: 9, skill: 'strike', skillText: 'は のどもとに くらいついた！', skillMul: 1.45 },
  stump_old: { name: 'ろうぼくキリカブー', model: 'Mon_Stump', scale: 1.3, recolor: { StumpBark: '#4c4038', StumpBarkDark: '#2a221c', StumpLeaf: '#9a7a2a', StumpEye: '#ff5030', StumpRing: '#b89a78' }, hp: 38, atk: 25, def: 22, agi: 4, exp: 20, gold: 18, skill: 'strike', skillText: 'は ふといえだを たたきつけた！', skillMul: 1.5 },
  snake_cobra: { name: 'ドクコブラ', model: 'Mon_Snake', scale: 1.15, recolor: { SnakeScale: '#5c3a8a', SnakeScaleDark: '#2a1640', SnakeBelly: '#e8d070', SnakeIris: '#ff3030' }, hp: 30, atk: 27, def: 12, agi: 20, exp: 18, gold: 16, skill: 'strike', skillText: 'は もうどくの きばで かみついた！', skillMul: 1.45 },
  wolf_silver: { name: 'ぎんろうウルフ', model: 'Mon_Wolf', scale: 1.15, recolor: { WolfFur: '#a9adb8', WolfFurDark: '#565b6a', WolfFurLight: '#f0f2f6' }, hp: 46, atk: 36, def: 18, agi: 30, exp: 34, gold: 26, skill: 'strike', skillText: 'は するどい キバで かみくだいた！', skillMul: 1.45 },
  // ---- 浜辺
  crab: { name: 'ハサミガニ', model: 'Mon_Crab', scale: 1.0, hp: 22, atk: 15, def: 16, agi: 5, exp: 8, gold: 10, skill: 'strike', skillText: 'は おおきな ハサミで はさみこんだ！', skillMul: 1.5 },
  crab_armor: { name: 'よろいガニ', model: 'Mon_Crab', scale: 1.25, recolor: { CrabShell: '#3a6ea8', CrabShellDark: '#1c3560', CrabBelly: '#dfe8f0' }, hp: 44, atk: 30, def: 32, agi: 8, exp: 28, gold: 26, skill: 'strike', skillText: 'は はがねの ハサミで はさみこんだ！', skillMul: 1.5 },
  // ---- 夜・ダンジョン
  wisp: { name: 'おにび', model: 'Mon_Wisp', scale: 1.0, hp: 18, atk: 16, def: 10, agi: 20, exp: 12, gold: 12, skill: 'fire' },
  wisp_blue: { name: 'あおおにび', model: 'Mon_Wisp', scale: 1.15, recolor: { FlameCore: '#d8f0ff', FlameMid: '#4a90ff' }, hp: 36, atk: 30, def: 20, agi: 32, exp: 30, gold: 28, skill: 'fire' },
  skeleton: { name: 'ほねせんし', model: 'Mon_Skeleton', scale: 1.0, hp: 40, atk: 30, def: 18, agi: 14, exp: 26, gold: 24, skill: 'strike', skillText: 'は さびた つるぎで きりかかった！', skillMul: 1.35 },
  skeleton_dark: { name: 'やみのほねせんし', model: 'Mon_Skeleton', scale: 1.1, recolor: { SkelBone: '#8a7f9c', SkelBoneDark: '#4a405a', SkullGlow: '#40a0ff', RustIron: '#2a2830', Rust: '#3a2a4a', SkelCloth: '#20304a' }, hp: 62, atk: 40, def: 26, agi: 20, exp: 46, gold: 40, skill: 'strike', skillText: 'は やみの つるぎで きりさいた！', skillMul: 1.4 },
  gargoyle: { name: 'ガーゴイル', model: 'Mon_Gargoyle', scale: 1.0, hp: 58, atk: 38, def: 30, agi: 26, exp: 44, gold: 38, skill: 'strike', skillText: 'は きゅうこうかして ツメで きりさいた！', skillMul: 1.4 },
  guardian: {
    name: 'がんせきの番人', model: 'Mon_Golem', scale: 1.55, boss: true, guardian: true,
    recolor: { GolemRock: '#77708a', GolemRockDark: '#4c4860', Moss: '#5f8796' },
    hp: 190, atk: 44, def: 30, agi: 10, exp: 160, gold: 260, skill: 'smash',
  },
  dragon: {
    name: '魔竜ヴァルザード', model: 'Mon_Dragon', scale: 1.15, boss: true,
    hp: 520, atk: 60, def: 42, agi: 34, exp: 0, gold: 0, skill: 'breath',
  },
};

/** 地域の危険度から出現テーブルを決める */
export function encounterTable(x, z, night, h = 10) {
  const d = Math.hypot(x - -40, z - 60);
  let lv = 1 + d / 75;
  if (z < -100) lv += 2;
  lv = Math.max(1, Math.min(6, Math.floor(lv)));
  const T = {
    1: ['purun', 'purun', 'mushroom', 'stump'],
    2: ['purun', 'mushroom', 'bat', 'purun_red', 'stump', 'snake'],
    3: ['mushroom', 'bat', 'purun_red', 'snake', 'wolf', 'stump'],
    4: ['bat', 'purun_red', 'mushroom_poison', 'ghost', 'wolf', 'snake_cobra', 'stump_old'],
    5: ['mushroom_poison', 'bat_dark', 'ghost', 'golem', 'wolf_silver', 'snake_cobra', 'stump_old'],
    6: ['golem', 'bat_dark', 'ghost_blue', 'mushroom_poison', 'wolf_silver', 'skeleton'],
  }[lv].slice();
  // 浜辺ではカニが多い
  if (h < 2.6) T.push(...(lv >= 4 ? ['crab_armor', 'crab_armor', 'crab'] : ['crab', 'crab', 'crab']));
  if (night) T.push(...(lv >= 4 ? ['ghost_blue', 'wisp', 'skeleton'] : ['ghost', 'wisp']));
  return { lv, list: T };
}

export const SPELLS = {
  heal: { name: 'ヒール', mp: 3, target: 'ally', field: true, desc: 'なかま1人の HPを 30ほど かいふく', power: [28, 36] },
  highheal: { name: 'ハイヒール', mp: 6, target: 'ally', field: true, desc: 'なかま1人の HPを 100ほど かいふく', power: [90, 110] },
  healall: { name: 'ヒールオール', mp: 9, target: 'allies', field: true, desc: 'なかま全員の HPを 45ほど かいふく', power: [40, 52] },
  revive: { name: 'リザレク', mp: 12, target: 'dead', field: true, desc: 'たおれた なかまを いきかえらせる' },
  fire: { name: 'ファイア', mp: 3, target: 'one', desc: 'てき1たいを ほのおで こうげき', power: [14, 20], fx: 'fire' },
  storm: { name: 'フレイムストーム', mp: 8, target: 'all', desc: 'てき全体を ほのおの うずで つつむ', power: [26, 36], fx: 'storm' },
  blizzard: { name: 'ブリザード', mp: 7, target: 'one', desc: 'こおりの あらしで 大ダメージ', power: [42, 54], fx: 'ice' },
  lightning: { name: 'ライトニング', mp: 6, target: 'one', desc: 'いかずちで 大ダメージ', power: [34, 44], fx: 'lightning' },
  lightbreak: { name: 'ライトブレイク', mp: 15, target: 'one', desc: 'ひかりの つるぎで 会心の一撃', power: [120, 150], fx: 'light' },
  warcry: { name: 'おたけび', mp: 0, target: 'all', desc: 'てき全体を ひるませ ダメージ', power: [10, 16], fx: 'roar', skill: true },
  smashall: { name: 'だいせんぷう', mp: 0, target: 'all', desc: 'おのを ふりまわし てき全体を きる', power: [0, 0], fx: 'whirl', skill: true, melee: 0.75 },
  warp: { name: 'リターン', mp: 4, target: 'field', field: true, desc: 'アルセリア城に もどる' },
};

/** パーティメンバー：成長・習得呪文（習得レベル）・初期装備 */
export const MEMBERS = {
  hero: {
    name: null, model: 'Hero', role: 'ゆうしゃ',
    base: { hp: 24, mp: 6, str: 9, agi: 7 }, grow: { hp: 9, mp: 3.6, str: 3.4, agi: 2.6 },
    spells: { heal: 2, warp: 5, lightning: 8, lightbreak: 15 },
    equip: { weapon: 'sword_copper', armor: 'armor_cloth', shield: 'shield_leather' },
  },
  milia: {
    name: 'ミリア', model: 'Milia', role: 'まほうつかい', minLv: 2,
    base: { hp: 16, mp: 14, str: 5, agi: 9 }, grow: { hp: 6, mp: 5.5, str: 1.8, agi: 2.9 },
    spells: { fire: 1, storm: 6, blizzard: 10 },
    equip: { weapon: 'staff_oak', armor: 'robe_silk', shield: null },
  },
  gald: {
    name: 'ガルド', model: 'Gald', role: 'せんし', minLv: 4,
    base: { hp: 34, mp: 0, str: 13, agi: 5 }, grow: { hp: 11, mp: 0, str: 4.2, agi: 2.0 },
    spells: { warcry: 4, smashall: 9 },
    equip: { weapon: 'axe_iron', armor: 'armor_chain', shield: null },
  },
  serena: {
    name: 'セレナ', model: 'Serena', role: 'しんかん', minLv: 6,
    base: { hp: 20, mp: 16, str: 6, agi: 8 }, grow: { hp: 7, mp: 5.2, str: 2.0, agi: 2.5 },
    spells: { heal: 1, highheal: 5, healall: 8, revive: 11 },
    equip: { weapon: 'staff_holy', armor: 'robe_silk', shield: null },
  },
};

export const ITEMS = {
  herb: { name: 'やくそう', price: 8, desc: 'HPを 35ほど かいふく', use: 'heal', power: [30, 40] },
  ether: { name: 'まほうのせいすい', price: 60, desc: 'MPを 20 かいふく', use: 'mp', power: [20, 20] },
  wing: { name: 'てんいのはね', price: 25, desc: 'アルセリア城に もどる', use: 'warp', fieldOnly: true },
};

export const EQUIP = {
  sword_copper: { name: 'どうのつるぎ', slot: 'weapon', atk: 6, price: 100 },
  staff_oak: { name: 'かしのつえ', slot: 'weapon', atk: 3, price: 40 },
  staff_holy: { name: 'せいなるつえ', slot: 'weapon', atk: 6, price: 300 },
  axe_iron: { name: 'てつのおの', slot: 'weapon', atk: 18, price: 500 },
  robe_silk: { name: 'シルクのローブ', slot: 'armor', def: 7, price: 150 },
  sword_iron: { name: 'てつのつるぎ', slot: 'weapon', atk: 15, price: 380 },
  sword_steel: { name: 'はがねのつるぎ', slot: 'weapon', atk: 26, price: 1300 },
  sword_light: { name: 'ひかりのつるぎ', slot: 'weapon', atk: 42, price: 3800 },
  armor_cloth: { name: 'たびびとのふく', slot: 'armor', def: 4, price: 30 },
  armor_leather: { name: 'かわのよろい', slot: 'armor', def: 11, price: 180 },
  armor_chain: { name: 'くさりかたびら', slot: 'armor', def: 19, price: 520 },
  armor_steel: { name: 'はがねのよろい', slot: 'armor', def: 32, price: 1600 },
  shield_leather: { name: 'かわのたて', slot: 'shield', def: 3, price: 60 },
  shield_iron: { name: 'てつのたて', slot: 'shield', def: 10, price: 420 },
  shield_light: { name: 'ひかりのたて', slot: 'shield', def: 20, price: 2600 },
};

/** 宝箱の中身（フロアID-番号） */
export const CHESTS = {
  'cave1-0': { item: 'herb', n: 3 },
  'cave1-1': { gold: 180 },
  'cave1-2': { equip: 'shield_iron' },
  'cave1-3': { item: 'ether', n: 1 },
  'cave2-0': { equip: 'sword_steel' },
  'cave2-1': { gold: 350 },
  'tower1-0': { item: 'ether', n: 2 },
  'tower1-1': { item: 'herb', n: 4 },
  'tower2-0': { equip: 'armor_steel' },
  'tower2-1': { gold: 600 },
  'tower2-2': { equip: 'sword_light' },
};

export const SHOP = ['herb', 'ether', 'wing', 'sword_iron', 'sword_steel', 'sword_light', 'armor_leather', 'armor_chain', 'armor_steel', 'shield_iron', 'shield_light'];

export const MAX_LV = 50;
export function expForLevel(lv) { return lv <= 1 ? 0 : Math.round(9 * Math.pow(lv - 1, 2.35) + 6 * (lv - 1)); }


// ================================================================== 第二部：五つの島
// 島ごとのモンスター（モデルは Blender で作成。色ちがいは recolor）
Object.assign(MONSTERS, {
  // ---- 灼砂の島
  sandpurun: { name: 'すなぷるりん', model: 'Mon_Purun', scale: 1.3, recolor: { Gel: '#e8c070', SproutLeaf: '#7a8a3a' }, hp: 95, atk: 112, def: 40, agi: 30, exp: 70, gold: 40 },
  cactus: { name: 'トゲサボテン', model: 'Mon_Cactus', scale: 1.0, hp: 125, atk: 120, def: 58, agi: 22, exp: 85, gold: 55, skill: 'allhit', skillText: 'は トゲを まわりに うちだした！', skillMul: 0.6 },
  scorpion: { name: 'デザートスコーピオン', model: 'Mon_Scorpion', scale: 1.0, hp: 145, atk: 136, def: 72, agi: 45, exp: 95, gold: 60, skill: 'strike', skillText: 'は どくばりで つきさした！', skillMul: 1.5 },
  mummy: { name: 'ミイラおとこ', model: 'Mon_Mummy', scale: 1.0, hp: 175, atk: 130, def: 50, agi: 25, exp: 105, gold: 70, skill: 'strike', skillText: 'は ほうたいで しめつけた！', skillMul: 1.4 },
  sandsnake: { name: 'スナコブラ', model: 'Mon_Snake', scale: 1.25, recolor: { SnakeScale: '#c8a050', SnakeScaleDark: '#6a4a20', SnakeBelly: '#f0e0b0', SnakeIris: '#40ff80' }, hp: 125, atk: 128, def: 45, agi: 62, exp: 90, gold: 55, skill: 'strike', skillText: 'は すなに もぐって かみついた！', skillMul: 1.45 },
  giltab: { name: 'だいサソリ ギルタブ', model: 'Mon_Scorpion', scale: 2.3, boss: true, mid: true, recolor: { ScorpShell: '#d8a030', ScorpShellDark: '#3a2410', ScorpEye: '#ff3020' }, hp: 1400, atk: 150, def: 75, agi: 40, exp: 1500, gold: 1200, skill: 'strike', skillText: 'は きょだいな ハサミで はさみこんだ！', skillMul: 1.6 },
  anubis: { name: '砂の魔将 アヌビス', model: 'Mon_Anubis', scale: 1.5, boss: true, hp: 2400, atk: 165, def: 80, agi: 70, exp: 3000, gold: 2500, skill: 'magicall', skillText: 'は すなあらしの のろいを となえた！', skillPow: [55, 75], fxColor: [0xe8c070, 0xff9a40, 0xffffff] },
  // ---- 氷雪の島
  icepurun: { name: 'こおりぷるりん', model: 'Mon_Purun', scale: 1.35, recolor: { Gel: '#9fe0ff', SproutLeaf: '#e0f8ff' }, hp: 175, atk: 145, def: 70, agi: 40, exp: 140, gold: 70 },
  snowman: { name: 'ゆきだるまん', model: 'Mon_Snowman', scale: 1.0, hp: 235, atk: 150, def: 85, agi: 20, exp: 170, gold: 90, skill: 'magicall', skillText: 'は つめたい いきを ふきかけた！', skillPow: [40, 55], fxColor: [0xd0f0ff, 0xffffff, 0x80c0ff] },
  icewolf: { name: 'アイスウルフ', model: 'Mon_Wolf', scale: 1.15, recolor: { WolfFur: '#e8f4ff', WolfFurDark: '#8ab0d0', WolfFurLight: '#ffffff' }, hp: 215, atk: 165, def: 70, agi: 82, exp: 175, gold: 85, skill: 'strike', skillText: 'は こおりの キバで かみついた！', skillMul: 1.45 },
  penguin: { name: 'ペンギンナイト', model: 'Mon_Penguin', scale: 1.0, hp: 245, atk: 168, def: 92, agi: 55, exp: 185, gold: 100, skill: 'strike', skillText: 'は こおりの やりで つきさした！', skillMul: 1.45 },
  icewraith: { name: 'ひょうれい', model: 'Mon_Ghost', scale: 1.3, recolor: { Ghost: '#cfeeff', GhostSkirt: '#9fd8ff' }, hp: 195, atk: 150, def: 70, agi: 72, exp: 165, gold: 90, skill: 'magicall', skillText: 'は ふぶきを よびおこした！', skillPow: [45, 60], fxColor: [0xd0f0ff, 0xffffff, 0x80c0ff] },
  yeti: { name: 'イエティ', model: 'Mon_Yeti', scale: 1.6, boss: true, mid: true, hp: 2400, atk: 185, def: 95, agi: 50, exp: 2600, gold: 2000, skill: 'strike', skillText: 'は こおりの いわを なげつけた！', skillMul: 1.6 },
  glacia: { name: '氷竜 グレイシャ', model: 'Mon_Dragon', scale: 1.1, boss: true, recolor: { DragonScale: '#a8d8f0', DragonScaleDark: '#5080b0', DragonBelly: '#f0fbff', DragonWing: '#6aa8d8', DragonEye: '#40e0ff', Horn: '#e8f8ff' }, hp: 3600, atk: 200, def: 100, agi: 75, exp: 5000, gold: 4000, skill: 'magicall', skillText: 'は こごえる ふぶきを はいた！', skillPow: [70, 90], fxColor: [0xd0f0ff, 0xffffff, 0x60b0ff], breath: true },
  // ---- 炎獄の島
  lavapurun: { name: 'マグマぷるりん', model: 'Mon_Purun', scale: 1.35, recolor: { Gel: '#ff5a20', SproutLeaf: '#3a2a20' }, hp: 265, atk: 180, def: 90, agi: 50, exp: 230, gold: 110 },
  salamander: { name: 'サラマンダー', model: 'Mon_Lizard', scale: 1.0, hp: 320, atk: 200, def: 100, agi: 70, exp: 270, gold: 130, skill: 'magicall', skillText: 'は ほのおの いきを はいた！', skillPow: [55, 70], fxColor: [0xffdd66, 0xff7722, 0xff3300] },
  firebird: { name: 'ひのとり', model: 'Mon_Firebird', scale: 1.0, hp: 295, atk: 195, def: 90, agi: 110, exp: 260, gold: 125, skill: 'strike', skillText: 'は ほのおの つばさで きりさいた！', skillMul: 1.5 },
  magmagolem: { name: 'マグマゴーレム', model: 'Mon_Golem', scale: 1.1, recolor: { GolemRock: '#3a2a26', GolemRockDark: '#1e1614', Moss: '#ff5a10', GolemEye: '#ffb030' }, hp: 420, atk: 215, def: 130, agi: 20, exp: 300, gold: 150, skill: 'smash' },
  flamewisp: { name: 'ほのおのせい', model: 'Mon_Wisp', scale: 1.2, recolor: { FlameCore: '#fff0a0', FlameMid: '#ff3010' }, hp: 255, atk: 185, def: 95, agi: 96, exp: 240, gold: 120, skill: 'magicall', skillText: 'は ひばしらを たてた！', skillPow: [50, 66], fxColor: [0xffdd66, 0xff7722, 0xff3300] },
  magmalord: { name: 'マグマロード', model: 'Mon_Golem', scale: 1.9, boss: true, mid: true, recolor: { GolemRock: '#2e2220', GolemRockDark: '#120c0a', Moss: '#ff6a10', GolemEye: '#ffe060' }, hp: 3600, atk: 225, def: 130, agi: 40, exp: 4000, gold: 3000, skill: 'smash' },
  ifrit: { name: '炎の魔将 イフリート', model: 'Mon_Ifrit', scale: 1.5, boss: true, hp: 5200, atk: 240, def: 125, agi: 90, exp: 7000, gold: 5000, skill: 'magicall', skillText: 'は じごくの ほのおを よびだした！', skillPow: [85, 110], fxColor: [0xffdd66, 0xff5511, 0xff2200], breath: true },
  // ---- 闇の島
  shadow: { name: 'シャドー', model: 'Mon_Ghost', scale: 1.35, recolor: { Ghost: '#3a2a4a', GhostSkirt: '#20142a' }, hp: 360, atk: 220, def: 110, agi: 100, exp: 360, gold: 160, skill: 'magicall', skillText: 'は やみの ちからを はなった！', skillPow: [65, 85], fxColor: [0x8040ff, 0x301050, 0xffffff] },
  evileye: { name: 'デビルアイ', model: 'Mon_EvilEye', scale: 1.0, hp: 340, atk: 215, def: 105, agi: 120, exp: 350, gold: 160, skill: 'magicall', skillText: 'は あやしい ひかりを はなった！', skillPow: [60, 80], fxColor: [0xff3060, 0xffa0c0, 0xffffff] },
  darkknight: { name: 'やみのきし', model: 'Mon_DarkKnight', scale: 1.0, hp: 480, atk: 250, def: 140, agi: 70, exp: 420, gold: 200, skill: 'strike', skillText: 'は くろい つるぎで きりさいた！', skillMul: 1.45 },
  gargoyle_dark: { name: 'ブラックガーゴイル', model: 'Mon_Gargoyle', scale: 1.15, recolor: { GargStone: '#3a3444', GargStoneDark: '#1a1620', GargEye: '#ff3040', GargWing: '#2a1c30' }, hp: 400, atk: 235, def: 120, agi: 100, exp: 380, gold: 180, skill: 'strike', skillText: 'は きゅうこうかして ツメで きりさいた！', skillMul: 1.45 },
  skeleton_king: { name: 'がいこつおう', model: 'Mon_Skeleton', scale: 1.25, recolor: { SkelBone: '#e8d8a0', SkelBoneDark: '#8a7040', SkullGlow: '#ff40ff', RustIron: '#c8a040', Rust: '#802040', SkelCloth: '#601030' }, hp: 430, atk: 240, def: 125, agi: 80, exp: 400, gold: 190, skill: 'strike', skillText: 'は おうじゃの つるぎを ふりおろした！', skillMul: 1.5 },
  knightlord: { name: '暗黒騎士団長 ベリアス', model: 'Mon_DarkKnight', scale: 1.6, boss: true, mid: true, recolor: { KnightArmor: '#2a2030', KnightTrim: '#d8a040', KnightCape: '#801020', KnightEye: '#ff3020' }, hp: 5000, atk: 265, def: 150, agi: 80, exp: 6000, gold: 4000, skill: 'strike', skillText: 'は あんこくの いちげきを はなった！', skillMul: 1.65 },
  zenos: { name: '混沌王 ゼノス', model: 'Mon_Zenos', scale: 1.6, boss: true, final: true, hp: 9000, atk: 285, def: 150, agi: 110, exp: 0, gold: 0, skill: 'magicall', skillText: 'は こんとんの ほのおを はなった！', skillPow: [100, 130], fxColor: [0xa040ff, 0xff40a0, 0xffffff], breath: true },
});

/** 島ごとの出現テーブル（島のローカル座標・夜） */
export function islandEncounter(id, x, z, night, h) {
  const T = {
    desert: { lv: 22, list: ['sandpurun', 'cactus', 'scorpion', 'mummy', 'sandsnake', 'scorpion'], night: ['mummy', 'mummy', 'wisp'] },
    ice: { lv: 28, list: ['icepurun', 'snowman', 'icewolf', 'penguin', 'icewraith', 'icewolf'], night: ['icewraith', 'icewraith'] },
    volcano: { lv: 34, list: ['lavapurun', 'salamander', 'firebird', 'magmagolem', 'flamewisp', 'salamander'], night: ['flamewisp', 'firebird'] },
    dark: { lv: 40, list: ['shadow', 'evileye', 'darkknight', 'gargoyle_dark', 'skeleton_king', 'darkknight'], night: ['shadow', 'evileye'] },
  }[id];
  const list = T.list.slice();
  if (night) list.push(...T.night);
  return { lv: T.lv, list };
}

/** 島のダンジョンの中ボス・ボス（フロア ID → 記号 B の位置に置く） */
export const ISLAND_BOSSES = {
  pyr1: { key: 'giltab', flag: 'b_giltab', range: 7, lines: [{ who: 'ギルタブ', text: 'キシャアアア……！ ファラオの ねむりを さまたげる ものは ゆるさぬ！' }] },
  pyr2: { key: 'anubis', flag: 'b_anubis', range: 7, orb: 'desert', lines: [{ who: 'アヌビス', text: 'ほう…… 竜を てなずけた ゆうしゃか。' }, { who: 'アヌビス', text: 'ゼノスさまの ために、 この 砂の せいれいは わたさぬ！ すなに かえるがよい！' }] },
  ice1: { key: 'yeti', flag: 'b_yeti', range: 7, lines: [{ who: 'イエティ', text: 'ウオオオオ……！' }] },
  ice2: { key: 'glacia', flag: 'b_glacia', range: 10, orb: 'ice', lines: [{ who: 'グレイシャ', text: 'ヴァルザード…… にんげんに くだったか。 おちぶれた ものよ。' }, { who: 'グレイシャ', text: 'こおりの せいれいは わが ちからの みなもと。 えいえんの ねむりに つくがよい！' }] },
  lava1: { key: 'magmalord', flag: 'b_magmalord', range: 8, lines: [{ who: 'マグマロード', text: 'ゴゴゴゴ……！ ここより さきへは ゆかせぬ！' }] },
  lava2: { key: 'ifrit', flag: 'b_ifrit', range: 8, orb: 'volcano', lines: [{ who: 'イフリート', text: 'ククク…… アヌビスも グレイシャも やぶったか。 だが ここまでだ。' }, { who: 'イフリート', text: 'ほのおの せいれいごと、 はいに してくれよう！' }] },
  dark1: { key: 'knightlord', flag: 'b_knightlord', range: 8, lines: [{ who: 'ベリアス', text: 'われは 暗黒騎士団長 ベリアス。 ゼノスさまの もとへは いかせん！' }] },
  dark2: { key: 'zenos', flag: 'b_zenos', range: 11, final: true, lines: [{ who: 'ゼノス', text: 'よくぞ きた、 ひかりの ゆうしゃよ。 そして うらぎりの 竜よ。' }, { who: 'ゼノス', text: 'この せかいの ひかりも やみも、 すべては こんとんに かえる。 それが さだめだ。' }, { who: 'ゼノス', text: 'さあ、 おまえたちの ひかりで わが こんとんを とめてみせよ！' }] },
};

// 第二部の そうび・どうぐ
Object.assign(ITEMS, {
  hiherb: { name: 'じょうやくそう', price: 60, desc: 'HPを 150ほど かいふく', use: 'heal', power: [140, 160] },
  elixir: { name: 'せいれいのしずく', price: 400, desc: 'HPを ぜんぶ かいふく', use: 'heal', power: [9999, 9999] },
  hiether: { name: 'まほうのせいすいＶ', price: 300, desc: 'MPを 60 かいふく', use: 'mp', power: [60, 60] },
});
Object.assign(EQUIP, {
  sword_scimitar: { name: 'さばくのシミター', slot: 'weapon', atk: 58, price: 2600 },
  axe_battle: { name: 'バトルアックス', slot: 'weapon', atk: 62, price: 2500 },
  staff_sun: { name: 'たいようのつえ', slot: 'weapon', atk: 24, price: 1800 },
  armor_scale: { name: 'うろこのよろい', slot: 'armor', def: 42, price: 2400 },
  robe_desert: { name: 'さばくのローブ', slot: 'armor', def: 26, price: 1600 },
  shield_bronze: { name: 'せいどうのたて', slot: 'shield', def: 26, price: 1800 },
  sword_ice: { name: 'こおりのやいば', slot: 'weapon', atk: 74, price: 4600 },
  axe_frost: { name: 'フロストアックス', slot: 'weapon', atk: 78, price: 4400 },
  staff_snow: { name: 'ゆきのつえ', slot: 'weapon', atk: 32, price: 3000 },
  armor_mithril: { name: 'ミスリルよろい', slot: 'armor', def: 56, price: 4800 },
  robe_mithril: { name: 'ミスリルローブ', slot: 'armor', def: 36, price: 3200 },
  shield_ice: { name: 'こおりのたて', slot: 'shield', def: 33, price: 3600 },
  sword_flame: { name: 'ほのおのつるぎ', slot: 'weapon', atk: 90, price: 7200 },
  axe_magma: { name: 'マグマアックス', slot: 'weapon', atk: 95, price: 6900 },
  staff_flame: { name: 'えんじゃのつえ', slot: 'weapon', atk: 40, price: 5000 },
  armor_dragon: { name: 'ドラゴンメイル', slot: 'armor', def: 72, price: 7600 },
  robe_dragon: { name: 'りゅうのはごろも', slot: 'armor', def: 47, price: 5200 },
  shield_dragon: { name: 'ドラゴンシールド', slot: 'shield', def: 42, price: 5600 },
  sword_hero: { name: 'ゆうしゃのつるぎ', slot: 'weapon', atk: 112, price: 12000 },
  axe_god: { name: 'はかいのおの', slot: 'weapon', atk: 116, price: 11500 },
  staff_angel: { name: 'てんしのつえ', slot: 'weapon', atk: 48, price: 8000 },
  armor_hero: { name: 'ゆうしゃのよろい', slot: 'armor', def: 90, price: 13000 },
  robe_angel: { name: 'てんしのローブ', slot: 'armor', def: 60, price: 9000 },
  shield_hero: { name: 'ゆうしゃのたて', slot: 'shield', def: 54, price: 9500 },
});

export const SHOPS = {
  desert: ['herb', 'hiherb', 'ether', 'wing', 'sword_scimitar', 'axe_battle', 'staff_sun', 'armor_scale', 'robe_desert', 'shield_bronze'],
  ice: ['hiherb', 'ether', 'hiether', 'wing', 'sword_ice', 'axe_frost', 'staff_snow', 'armor_mithril', 'robe_mithril', 'shield_ice'],
  volcano: ['hiherb', 'hiether', 'elixir', 'wing', 'sword_flame', 'axe_magma', 'staff_flame', 'armor_dragon', 'robe_dragon', 'shield_dragon'],
  dark: ['hiherb', 'hiether', 'elixir', 'wing', 'sword_hero', 'axe_god', 'staff_angel', 'armor_hero', 'robe_angel', 'shield_hero'],
};

// 第二部の じゅもん・とくぎ
Object.assign(SPELLS, {
  gigaslash: { name: 'ギガスラッシュ', mp: 18, target: 'all', desc: 'いかずちの つるぎで てき全体を きる', power: [150, 190], fx: 'lightning' },
  gigabreak: { name: 'ギガブレイク', mp: 30, target: 'all', desc: 'てんの いかずちを てき全体に おとす', power: [260, 320], fx: 'lightning' },
  meteor: { name: 'メテオ', mp: 20, target: 'all', desc: 'いんせきを ふらせ てき全体に 大ダメージ', power: [130, 165], fx: 'storm' },
  flare: { name: 'フレア', mp: 26, target: 'one', desc: 'ちょうこうねつで てき1たいに 大ダメージ', power: [320, 380], fx: 'fire' },
  ultima: { name: 'アルテマ', mp: 45, target: 'all', desc: 'すべてを やきつくす きゅうきょくの じゅもん', power: [300, 360], fx: 'storm' },
  kabuto: { name: 'かぶとわり', mp: 0, target: 'one', desc: 'てき1たいの かぶとごと たたきわる', power: [0, 0], fx: 'whirl', skill: true, melee: 1.7 },
  jinrai: { name: 'じんらいぎり', mp: 0, target: 'all', desc: 'いかずちの ように てき全体を きる', power: [0, 0], fx: 'whirl', skill: true, melee: 1.15 },
  fullheal: { name: 'フルヒール', mp: 14, target: 'ally', field: true, desc: 'なかま1人の HPを ぜんぶ かいふく', power: [9999, 9999] },
  saintheal: { name: 'セイントヒール', mp: 22, target: 'allies', field: true, desc: 'なかま全員の HPを 180ほど かいふく', power: [160, 200] },
  holy: { name: 'ホーリー', mp: 24, target: 'all', desc: 'せいなる ひかりで てき全体を うつ', power: [180, 230], fx: 'light' },
});
Object.assign(MEMBERS.hero.spells, { highheal: 20, gigaslash: 24, gigabreak: 36 });
Object.assign(MEMBERS.milia.spells, { meteor: 22, flare: 30, ultima: 40 });
Object.assign(MEMBERS.gald.spells, { kabuto: 18, jinrai: 30 });
Object.assign(MEMBERS.serena.spells, { fullheal: 20, saintheal: 28, holy: 34 });

// 島のダンジョンの宝箱
Object.assign(CHESTS, {
  'pyr1-0': { item: 'hiherb', n: 3 }, 'pyr1-1': { gold: 1500 }, 'pyr1-2': { equip: 'shield_bronze' },
  'pyr2-0': { equip: 'sword_scimitar' }, 'pyr2-1': { item: 'hiether', n: 2 },
  'ice1-0': { item: 'hiherb', n: 4 }, 'ice1-1': { gold: 2600 }, 'ice1-2': { equip: 'robe_mithril' },
  'ice2-0': { equip: 'sword_ice' }, 'ice2-1': { item: 'elixir', n: 1 },
  'lava1-0': { item: 'hiether', n: 2 }, 'lava1-1': { gold: 4200 }, 'lava1-2': { equip: 'shield_dragon' },
  'lava2-0': { equip: 'armor_dragon' }, 'lava2-1': { item: 'elixir', n: 2 },
  'dark1-0': { item: 'elixir', n: 2 }, 'dark1-1': { equip: 'sword_hero' }, 'dark1-2': { gold: 8000 },
  'dark2-0': { equip: 'shield_hero' }, 'dark2-1': { item: 'hiether', n: 3 },
});

/** 会話。関数は (game) を受け取り、行の配列を返す */
export const TALK = {
  King: (g) => {
    const s = g.state;
    if (s.flags.cleared2) return [
      { who: '王さま', text: `おお ${s.name}！ せかいを すくった えいゆうよ！` },
      { who: '王さま', text: 'これからも ヴァルザードと ともに、 五つの しまを みまもってくれ。', action: 'save' },
      { text: 'ぼうけんの しょに きろくしました。', se: 'save' },
    ];
    if (s.flags.sequel) {
      const n = ['desert', 'ice', 'volcano'].filter((k) => s.flags['orb_' + k]).length;
      return [
        { who: '王さま', text: `おお ${s.name}！ せいれいの ほうじゅは ${n}つ あつまったか。` },
        { who: '王さま', text: n >= 3 ? 'みなみの 闇の島へ ゆくのじゃ！ ゼノスを たおし、 せかいに ひかりを！' : 'ひがしの 灼砂の島、 きたの 氷雪の島、 にしの 炎獄の島。 のこる しまへ ヴァルザードと むかうのじゃ。' },
        { who: '王さま', text: 'これまでの ぼうけんを きろく しておこう。', action: 'save' },
        { text: 'ぼうけんの しょに きろくしました。', se: 'save' },
      ];
    }
    if (s.flags.cleared) return [
      { who: '王さま', text: `おお ${s.name}！ そなたこそ まことの ゆうしゃじゃ。` },
      { who: '王さま', text: 'せかいに ひかりが もどった。 これからも この国を みまもってくれ。' },
    ];
    if (!s.flags.metKing) {
      s.flags.metKing = true;
      g.state.gold += 120;
      g.addItem('herb', 3);
      return [
        { who: '王さま', text: `おお ${s.name}よ！ よくぞ まいった。` },
        { who: '王さま', text: 'きたの やまの おくに そびえる 「まおうの塔」に 魔竜ヴァルザードが すみつき、 せかいは やみに のみこまれようと しておる。' },
        { who: '王さま', text: 'どうか 魔竜を たおし、 この国に ひかりを とりもどしてくれ！' },
        { who: '王さま', text: 'わずかだが たびの しきんじゃ。 うけとるがよい。' },
        { text: `${s.name}は 120ゴールドと やくそうを 3こ うけとった！`, se: 'item' },
        { who: '王さま', text: 'ひがしの ミナトの村で そうびを ととのえるのじゃ。 村の 長老なら 塔への みちを しっておろう。' },
        { who: '王さま', text: 'では ゆけ、 ゆうしゃよ！' },
      ];
    }
    const hero = s.party[0];
    const need = hero.lv >= MAX_LV ? 0 : expForLevel(hero.lv + 1) - hero.exp;
    return [
      { who: '王さま', text: `おお ${s.name}！ よくぞ もどった。` },
      need > 0 ? { who: '王さま', text: `そなたが つぎの レベルに なるには あと ${need}ポイントの けいけんが ひつようじゃ。` }
        : { who: '王さま', text: 'そなたは もはや さいきょうの せんしじゃ！' },
      { who: '王さま', text: 'これまでの ぼうけんを きろく しておこう。', action: 'save' },
      { text: 'ぼうけんの しょに きろくしました。', se: 'save' },
      { who: '王さま', text: 'では また あおう！' },
    ];
  },
  Guard1: () => [{ who: 'へいし', text: 'ここは アルセリア城。 王さまが あなたを おまちです。' }],
  Guard2: () => [{ who: 'へいし', text: '城の きたの みちを すすむと まおうの塔が あるそうだ。 だが いまの あなたでは…。' }],
  Guard3: () => [{ who: 'へいし', text: 'そとには まものが うろついている。 からだを きずつけたら 城に もどって やすむのだぞ。' }],
  Guard4: (g) => [{ who: 'へいし', text: g.sky.night > 0.5 ? 'よるは まものが つよくなる。 きをつけろ。' : 'いい てんきだな。 たびびとには もってこいの 日だ。' }],
  Minister: () => [
    { who: '大臣', text: 'ゆうしゃどの。 まものの すがたが みえたら、 ぶつかると たたかいに なりますぞ。' },
    { who: '大臣', text: 'つよい まものからは にげるのも ゆうきの ひとつ。 ちょうしに のりすぎぬ ことですな。' },
  ],
  Elder: (g) => g.state.flags.orb ? [
    { who: '長老', text: 'おお、 それは ひかりのオーブ！ それが あれば まおうの塔の ふういんも とけるじゃろう。' },
    { who: '長老', text: '魔竜の ほのおは すさまじい。 レベル 13は ほしいところじゃな。 ハイヒールを おぼえて おくとよい。' },
  ] : [
    { who: '長老', text: 'まおうの塔の とびらは やみの ふういんで とざされておる。' },
    { who: '長老', text: 'にしの いわやまの ふもとに 「ほこらの洞窟」が ある。 その おくに ねむる 「ひかりのオーブ」なら ふういんを やぶれるはずじゃ。' },
    { who: '長老', text: 'ただし オーブは いわの 番人が まもっておる。 じゅうぶん つよく なってから いくのじゃぞ。 レベル 8は ほしいの。' },
  ],
  Girl: (g) => [{ who: 'むすめ', text: g.sky.night > 0.5 ? 'よるに なると ゴーストが でるんだって。 こわーい！' : 'ねえねえ、 そらの くもって たべられるのかなあ？' }],
  Villager1: () => [{ who: 'むらびと', text: 'やくそうは だいじに つかえよ。 HPが あかく なったら すぐ つかうんだ。' }],
  Villager2: () => [{ who: 'むらびと', text: 'ほしの きれいな よるは、 ふしぎと まものも ざわつく きが するんだ。' }],
  Resident1: (g) => [{ who: 'むらびと', text: g.state.flags.cleared ? 'まおうの塔の やみが きえたんだって？ これで あんしんして ねむれるよ。' : 'よるは まどを しめて ねるんだ。 まものの なきごえが こわくてね。' }],
  Resident2: () => [{ who: 'むすめ', text: 'つぼや たるの なかを しらべると、 たまに いいものが はいってるのよ。 ないしょね！' }],
  Sign1: () => [{ text: '「 ↑ まおうの塔　　→ ミナトの村 」' }],
  Sign2: () => [{ text: '「 ← アルセリア城　　↑ まおうの塔 」\nこのさき まものが つよくなる。' }],
  Sign3: () => [{ text: '「 ミナトの村 　やすらぎと たびの みなと 」' }],
  Sign4: () => [{ text: '「 ↖ ほこらの洞窟　　↑ まおうの塔 」' }],
};

// ---- 第二部：島の人びと
Object.assign(TALK, {
  DesertElder: (g) => (g.state.flags.orb_desert ? [
    { who: 'オアシスの長', text: 'すなあらしが やんだ……。 すなの せいれいさまが もどられたのじゃな。 ほんとうに ありがとう。' },
  ] : [
    { who: 'オアシスの長', text: 'ひがしの ピラミッドに 「砂の魔将 アヌビス」が すみつき、 すなの せいれいさまを とらえて しもうた。' },
    { who: 'オアシスの長', text: 'ピラミッドの 1かいには きょだいな サソリが まちかまえておる。 どくに きをつけるのじゃぞ。 レベル 22は ほしいのう。' },
  ]),
  DesertGirl: (g) => [{ who: 'むすめ', text: g.sky.night > 0.5 ? 'よるの さばくは さむいの。 ミイラが あるきまわるから そとに でちゃ だめって。' : 'りゅうに のって きたの！？ いいなあ、 わたしも そらを とんでみたい！' }],
  DesertTrader: () => [{ who: 'しょうにん', text: 'サボテンの トゲは みんなに ささるから やっかいだぜ。 HPは いつも まんたんに しておきな。' }],
  DesertGuard: () => [{ who: 'みはり', text: 'ここは オアシスの町 ルミナ。 まものは ここまで はいってこないから あんしんして やすんでいけ。' }],
  IceElder: (g) => (g.state.flags.orb_ice ? [
    { who: '村長', text: 'ふぶきが おさまった。 こおりの せいれいさまが かえってこられたのだな。' },
  ] : [
    { who: '村長', text: 'きたの こおりの きゅうでんに 「氷竜グレイシャ」が いすわり、 こおりの せいれいさまを とじこめてしまった。' },
    { who: '村長', text: 'きゅうでんの いりぐちには おおきな イエティが いる。 ちからが つよいから、 ぼうぎょも だいじだぞ。 レベル 28は ほしい。' },
  ]),
  IceKid: () => [{ who: 'こども', text: 'ゆきだるまが うごいたんだよ！ ほんとだって！ ……え、 しってる？' }],
  IceHunter: () => [{ who: 'かりうど', text: 'アイスウルフは すばやい。 むれで おそってくるから、 ぜんたいこうげきで まとめて たおすんだ。' }],
  IceGuard: () => [{ who: 'みはり', text: 'この さきは こおりの きゅうでん。 ふぶきで まえが みえなくなる。 じゅんびは いいか？' }],
  SmithElder: (g) => (g.state.flags.orb_volcano ? [
    { who: '里長', text: 'ひのやまが しずかに なった。 ほのおの せいれいさまの おかげで、 炉の ひも あたたかい。' },
  ] : [
    { who: '里長', text: 'ひのやまの どうくつの おくで 「炎の魔将 イフリート」が ほのおの せいれいさまを とらえている。' },
    { who: '里長', text: 'あの ほのおは すさまじい。 ぜんいんの HPを すぐに なおせる ように しておけ。 レベル 34は ほしいぞ。' },
  ]),
  SmithBoy: () => [{ who: 'でし', text: 'うちの おやかたの きたえた ぶきは せかいいち！ ……みせで うってるよ、 たかいけどね。' }],
  SmithMaster: () => [{ who: 'かじや', text: 'マグマゴーレムは かたい。 まほうで せめるか、 ちからまかせに たたきわるかだ。' }],
  RebelLeader: (g) => (g.state.flags.b_knightlord ? [
    { who: 'リーダー', text: 'ベリアスを たおしたのか！ あとは ゼノスだけだ。 たのむ、 この しまを すくってくれ！' },
  ] : [
    { who: 'リーダー', text: 'よく きてくれた、 ひかりの ゆうしゃ。 われらは ゼノスに あらがう レジスタンスだ。' },
    { who: 'リーダー', text: 'こんとんの しろの 1かいは 暗黒騎士団長 ベリアスが まもっている。 その おくに ゼノスの ぎょくざが ある。 レベル 40は ほしい。' },
  ]),
  RebelSoldier: () => [{ who: 'へいし', text: 'デビルアイの あやしい ひかりは いたいぞ。 さきに たおしてしまえ。' }],
  RebelGirl: () => [{ who: 'しょうじょ', text: 'いつか この しまにも あかるい そらが もどるよね？' }],
  RebelOld: () => [{ who: 'ろうじん', text: 'むかし この しまは 「ほしの しま」と よばれる うつくしい しまじゃった……。' }],
});
