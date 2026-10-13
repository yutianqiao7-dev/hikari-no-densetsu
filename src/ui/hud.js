import { derived, memberName } from '../game/state.js';

/** 画面左上のステータス、右上のミニマップと時計 */
export class HUD {
  constructor(game) {
    this.g = game;
    const root = game.ui.root;
    this.status = document.createElement('div');
    this.status.id = 'hud-party';
    root.appendChild(this.status);

    this.mapWrap = document.createElement('div');
    this.mapWrap.id = 'minimap';
    this.mapWrap.innerHTML = '<canvas width="256" height="256"></canvas><div class="n">N</div>';
    root.appendChild(this.mapWrap);
    this.map = this.mapWrap.querySelector('canvas');
    this.ctx = this.map.getContext('2d');
    this.north = this.mapWrap.querySelector('.n');

    this.clock = document.createElement('div');
    this.clock.id = 'clock';
    root.appendChild(this.clock);
    this.base = null;
    this.visible = true;
  }

  /** 地形の色から全体マップを作る（1 回だけ） */
  buildBaseMap(world) {
    const map = world.map;
    this.world = world;
    if (map.baseMap) { this.base = map.baseMap; return; }
    const hf = world.hf, W = hf.w;
    const c = document.createElement('canvas');
    c.width = c.height = W;
    const g = c.getContext('2d');
    const img = g.createImageData(W, W);
    const col = world.terrain.colors;
    const s = (x) => Math.round(255 * Math.min(1, Math.pow(Math.max(0, x), 1 / 2.2)));
    for (let j = 0; j < W; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, o = k * 4, h = hf.h[k];
      if (h < 0.15) {
        const d = Math.min(1, -h / 10);
        img.data[o] = 30 - d * 20; img.data[o + 1] = 110 - d * 60; img.data[o + 2] = 170 - d * 60;
      } else {
        const shade = 0.75 + Math.min(0.5, h / 120);
        img.data[o] = s(col[k * 3]) * shade; img.data[o + 1] = s(col[k * 3 + 1]) * shade; img.data[o + 2] = s(col[k * 3 + 2]) * shade;
      }
      img.data[o + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    // 木
    g.fillStyle = 'rgba(20,60,20,0.55)';
    for (const kind of Object.keys(world.data.scatter).filter((k) => /^Tree/.test(k))) for (const [x, , z] of world.data.scatter[kind] || []) {
      g.fillRect((x + hf.half) / hf.step - 0.6, (z + hf.half) / hf.step - 0.6, 1.2, 1.2);
    }
    const icon = (x, z, color, size, shape) => {
      const px = (x + hf.half) / hf.step, pz = (z + hf.half) / hf.step;
      g.fillStyle = color; g.strokeStyle = '#000'; g.lineWidth = 1;
      g.beginPath();
      if (shape === 'tri') { g.moveTo(px, pz - size); g.lineTo(px + size, pz + size); g.lineTo(px - size, pz + size); }
      else g.rect(px - size, pz - size, size * 2, size * 2);
      g.fill(); g.stroke();
    };
    if (map.id === 'main') {
      icon(-40, 60, '#e8e8ff', 6);
      icon(140, 110, '#ffd27a', 5);
      icon(70, -215, '#b060ff', 5, 'tri');
    } else {
      for (const a of Object.values(map.areas)) icon(a.x, a.z, '#ffd27a', 5);
      for (const [k, m] of Object.entries(map.markers)) if (/^Door_/.test(k)) icon(m.x, m.z, '#b060ff', 5, 'tri');
    }
    this.base = c;
    map.baseMap = c;
  }

  /** ダンジョンでは配置図から描いたマップに切り替える（null でフィールドに戻す） */
  setMapEnv(floor) {
    if (!floor) { this.mapEnv = null; return; }
    const px = 8;
    const c = document.createElement('canvas');
    c.width = floor.W * px; c.height = floor.H * px;
    const g = c.getContext('2d');
    const rockyS = ['cave', 'icecave', 'lava'].includes(floor.style);
    const col = { '#': { icecave: '#203448', lava: '#1a1210', pyramid: '#3a2c1a' }[floor.style] || (rockyS ? '#2a2420' : '#241c2c'), W: floor.style === 'lava' ? '#d04010' : floor.style === 'icecave' ? '#8ad0ff' : '#1d4a6a', P: '#6a6070', T: '#e08a30', S: '#fff0b0', U: '#9fd0ff', D: '#9fd0ff', C: '#e8c040', B: '#c040ff', O: '#ffe070' };
    for (let j = 0; j < floor.H; j++) for (let i = 0; i < floor.W; i++) {
      const ch = floor.grid[j][i];
      g.fillStyle = col[ch] || ({ icecave: '#a8c8e0', lava: '#5a4a44', pyramid: '#b89a70' }[floor.style] || (rockyS ? '#7a6a58' : '#8a8090'));
      g.fillRect(i * px, j * px, px, px);
    }
    this.mapEnv = { img: c, ox: floor.ox, oz: floor.oz, scale: floor.cell / px, floor };
  }

  /** パーティ全員のステータス（active はコマンド入力中のメンバー） */
  update(active) {
    const s = this.g.state;
    if (!s) return;
    this.status.innerHTML = s.party.map((m) => {
      const d = derived(m);
      const hpr = m.hp / d.maxHp;
      const cls = 'win member' + (m.hp <= 0 ? ' dead' : hpr < 0.3 ? ' danger' : '') + (active === m.id ? ' active' : '');
      return `<div class="${cls}">
        <div class="name">${memberName(s, m)}</div>
        <div class="row"><span>H</span><span>${m.hp}</span></div><div class="bar"><i style="width:${Math.max(0, hpr) * 100}%"></i></div>
        <div class="row"><span>M</span><span>${m.mp}</span></div><div class="bar mp"><i style="width:${d.maxMp ? (m.mp / d.maxMp) * 100 : 0}%"></i></div>
        <div class="row"><span class="lv">Lv</span><span class="lv">${m.lv}</span></div></div>`;
    }).join('');
  }

  setVisible(v) {
    this.visible = v;
    this.status.style.display = v ? '' : 'none';
    this.mapWrap.style.display = v ? '' : 'none';
    this.clock.style.display = v ? '' : 'none';
  }

  /** 毎フレーム：プレイヤー中心・カメラ向きに回転したミニマップ */
  tick(field, sky) {
    if (!this.base || !this.visible) return;
    const g = this.ctx, hf = this.world.hf;
    const me = this.mapEnv;
    const toMap = me ? (x, z) => [(x - me.ox) / me.scale, (z - me.oz) / me.scale] : (x, z) => [(x + hf.half) / hf.step, (z + hf.half) / hf.step];
    const [px, pz] = toMap(field.pos.x, field.pos.z);
    const zoom = me ? 1.6 : 2.4;
    g.save();
    g.fillStyle = '#123';
    g.fillRect(0, 0, 256, 256);
    g.translate(128, 128);
    g.rotate(field.cam.yaw);
    g.scale(zoom, zoom);
    g.translate(-px, -pz);
    g.imageSmoothingEnabled = true;
    g.imageSmoothingEnabled = !me;
    g.drawImage(me ? me.img : this.base, 0, 0);
    // モンスター
    g.fillStyle = '#ff4a3a';
    for (const m of field.mons) {
      const [mx, mz] = toMap(m.root.position.x, m.root.position.z);
      g.beginPath(); g.arc(mx, mz, me ? 2.2 : 1.3, 0, Math.PI * 2); g.fill();
    }
    if (!me) {
      g.fillStyle = '#ffffff';
      for (const n of field.npcs) {
        const [mx, mz] = toMap(n.pos.x, n.pos.z);
        g.beginPath(); g.arc(mx, mz, 0.8, 0, Math.PI * 2); g.fill();
      }
    }
    g.restore();
    // プレイヤー
    g.save();
    g.translate(128, 128);
    g.rotate(field.cam.yaw - field.facing + Math.PI);
    g.fillStyle = '#ffe14a';
    g.strokeStyle = '#000';
    g.lineWidth = 2;
    g.beginPath(); g.moveTo(0, -11); g.lineTo(8, 9); g.lineTo(0, 4); g.lineTo(-8, 9); g.closePath();
    g.fill(); g.stroke();
    g.restore();
    // 北の位置
    const a = field.cam.yaw;
    const r = this.mapWrap.clientWidth / 2 - 9;
    this.north.style.left = `${this.mapWrap.clientWidth / 2 + Math.sin(a) * r}px`;
    this.north.style.top = `${this.mapWrap.clientWidth / 2 - Math.cos(a) * r - 8}px`;
    const h = sky.hours;
    const hh = Math.floor(h), mm = Math.floor((h - hh) * 60);
    const icon = sky.night > 0.5 ? '☾' : '☀';
    this.clock.textContent = me ? me.floor.name : `${icon} ${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
  }
}
