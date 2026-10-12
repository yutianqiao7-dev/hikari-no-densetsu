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
export function encounterTable(x, z, night) {
  const d = Math.hypot(x - -40, z - 60);
  let lv = 1 + d / 75;
  if (z < -100) lv += 2;
  lv = Math.max(1, Math.min(6, Math.floor(lv)));
  const T = {
    1: ['purun', 'purun', 'mushroom'],
    2: ['purun', 'mushroom', 'bat', 'purun_red'],
    3: ['mushroom', 'bat', 'purun_red', 'purun_red'],
    4: ['bat', 'purun_red', 'mushroom_poison', 'ghost'],
    5: ['mushroom_poison', 'bat_dark', 'ghost', 'golem'],
    6: ['golem', 'bat_dark', 'ghost_blue', 'mushroom_poison'],
  }[lv].slice();
  if (night) T.push(lv >= 4 ? 'ghost_blue' : 'ghost', 'ghost');
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

export const MAX_LV = 20;
export function expForLevel(lv) { return lv <= 1 ? 0 : Math.round(9 * Math.pow(lv - 1, 2.35) + 6 * (lv - 1)); }


/** 会話。関数は (game) を受け取り、行の配列を返す */
export const TALK = {
  King: (g) => {
    const s = g.state;
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
