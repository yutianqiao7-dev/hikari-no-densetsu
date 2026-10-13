/**
 * 入力：タッチ（左半分=移動スティック / 右半分=カメラ回転 / ピンチ=ズーム / A・B・MENU ボタン）
 *       キーボード・マウス・ゲームパッド
 * onKey(k) に 'confirm' | 'cancel' | 'menu' | 'up' | 'down' | 'left' | 'right' を送る
 */
export class Input {
  constructor(canvas, uiRoot) {
    this.move = { x: 0, y: 0 };
    this.cam = { yaw: 0, pitch: 0, zoom: 0 };
    this.onKey = () => {};
    this.keys = new Set();
    this.isTouch = matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window;
    this.runToggle = true;
    this.stick = null;
    this.camPtr = new Map();
    this.enabled = true;
    this._navT = 0;
    this._navDir = null;

    // ---- タッチ UI
    const touch = document.createElement('div');
    touch.id = 'touch';
    touch.innerHTML = `
      <div id="stick-base"><div id="stick-knob"></div></div>
      <div class="tbtn" id="btn-a">A</div>
      <div class="tbtn" id="btn-b">B</div>
      <div class="tbtn" id="btn-menu">MENU</div>`;
    uiRoot.appendChild(touch);
    this.touchEl = touch;
    this.base = touch.querySelector('#stick-base');
    this.knob = touch.querySelector('#stick-knob');
    const bind = (id, k) => {
      const b = touch.querySelector(id);
      b.addEventListener('pointerdown', (e) => { e.preventDefault(); e.stopPropagation(); b.classList.add('press'); this.emit(k); });
      const up = () => b.classList.remove('press');
      b.addEventListener('pointerup', up); b.addEventListener('pointerleave', up); b.addEventListener('pointercancel', up);
    };
    bind('#btn-a', 'confirm');
    bind('#btn-b', 'cancel');
    bind('#btn-menu', 'menu');
    this.touchAllowed = false;
    this.setTouchVisible(false);

    // ---- ポインター（キャンバス上）
    canvas.addEventListener('pointerdown', (e) => this.down(e));
    window.addEventListener('pointermove', (e) => this.moveP(e));
    window.addEventListener('pointerup', (e) => this.up(e));
    window.addEventListener('pointercancel', (e) => this.up(e));
    canvas.addEventListener('wheel', (e) => { this.cam.zoom += Math.sign(e.deltaY) * 1.2; e.preventDefault(); }, { passive: false });
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    // ---- キーボード
    window.addEventListener('keydown', (e) => {
      if (e.target && e.target.tagName === 'INPUT') return;
      const k = e.key;
      this.keys.add(k.toLowerCase());
      const map = {
        ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right',
        Enter: 'confirm', ' ': 'confirm', z: 'confirm', Z: 'confirm',
        Escape: 'cancel', x: 'cancel', X: 'cancel', Backspace: 'cancel',
        m: 'menu', M: 'menu', Tab: 'menu',
      };
      if (map[k]) { this.emit(map[k]); e.preventDefault(); }
      if (!this.isTouch && ['w', 'a', 's', 'd'].includes(k.toLowerCase())) {
        this.emit({ w: 'up', s: 'down', a: 'left', d: 'right' }[k.toLowerCase()], true);
      }
    });
    window.addEventListener('keyup', (e) => this.keys.delete(e.key.toLowerCase()));
    window.addEventListener('blur', () => this.keys.clear());
  }

  setTouchVisible(v) {
    const on = v && this.touchAllowed;
    this.touchEl.style.display = on ? '' : 'none';
    // ボタンが出ているあいだは、文字のウィンドウをボタンの列にかぶらない位置へ
    document.body.classList.toggle('touch-on', !!on);
  }
  allowTouch(v) { this.touchAllowed = v; this.setTouchVisible(v && this.isTouch); }

  emit(k, soft) { if (this.enabled) this.onKey(k, soft); }

  down(e) {
    if (e.pointerType === 'mouse') {
      this.camPtr.set(e.pointerId, { x: e.clientX, y: e.clientY, mouse: true, moved: 0 });
      return;
    }
    this.isTouch = true;
    this.setTouchVisible(true);
    const left = e.clientX < window.innerWidth * 0.45;
    if (left && !this.stick) {
      this.stick = { id: e.pointerId, ox: e.clientX, oy: e.clientY };
      this.base.style.left = e.clientX + 'px';
      this.base.style.top = e.clientY + 'px';
      this.base.classList.add('on');
      this.knob.style.transform = 'translate(0,0)';
    } else {
      this.camPtr.set(e.pointerId, { x: e.clientX, y: e.clientY, moved: 0, t: performance.now() });
    }
  }

  moveP(e) {
    if (this.stick && e.pointerId === this.stick.id) {
      let dx = e.clientX - this.stick.ox, dy = e.clientY - this.stick.oy;
      const r = 52, len = Math.hypot(dx, dy);
      if (len > r) { dx *= r / len; dy *= r / len; }
      this.knob.style.transform = `translate(${dx}px, ${dy}px)`;
      this.move.x = dx / r;
      this.move.y = dy / r;
      return;
    }
    const p = this.camPtr.get(e.pointerId);
    if (!p) return;
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    p.moved += Math.abs(dx) + Math.abs(dy);
    if (this.camPtr.size >= 2) {
      // ピンチ
      p.x = e.clientX; p.y = e.clientY;
      const [a, b] = [...this.camPtr.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (this._pinch) this.cam.zoom -= (d - this._pinch) * 0.05;
      this._pinch = d;
      return;
    }
    if (p.mouse && !(e.buttons & 3)) return;
    this.cam.yaw -= dx * 0.006;
    this.cam.pitch += dy * 0.004;
    p.x = e.clientX; p.y = e.clientY;
  }

  up(e) {
    if (this.stick && e.pointerId === this.stick.id) {
      this.stick = null;
      this.move.x = this.move.y = 0;
      this.base.classList.remove('on');
      return;
    }
    const p = this.camPtr.get(e.pointerId);
    if (p && !p.mouse && p.moved < 10 && performance.now() - p.t < 300) this.onTap && this.onTap(e.clientX, e.clientY);
    if (p && p.mouse && p.moved < 6 && e.button === 0) this.onTap && this.onTap(e.clientX, e.clientY);
    this.camPtr.delete(e.pointerId);
    if (this.camPtr.size < 2) this._pinch = null;
  }

  /** 毎フレーム：キーボード・ゲームパッドの移動量を合成 */
  poll(dt, uiBusy) {
    let x = this.stick ? this.move.x : 0, y = this.stick ? this.move.y : 0;
    const K = this.keys;
    if (!uiBusy) {
      if (K.has('w') || K.has('arrowup')) y -= 1;
      if (K.has('s') || K.has('arrowdown')) y += 1;
      if (K.has('a') || K.has('arrowleft')) x -= 1;
      if (K.has('d') || K.has('arrowright')) x += 1;
      if (K.has('q')) this.cam.yaw += dt * 2.2;
      if (K.has('e')) this.cam.yaw -= dt * 2.2;
    }
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (const gp of pads) {
      if (!gp) continue;
      const dz = (v) => (Math.abs(v) < 0.18 ? 0 : v);
      x += dz(gp.axes[0] || 0); y += dz(gp.axes[1] || 0);
      this.cam.yaw -= dz(gp.axes[2] || 0) * dt * 2.5;
      this.cam.pitch += dz(gp.axes[3] || 0) * dt * 1.5;
      const prev = this._gp || [];
      const pressed = (i) => gp.buttons[i] && gp.buttons[i].pressed && !prev[i];
      if (pressed(0)) this.emit('confirm');
      if (pressed(1)) this.emit('cancel');
      if (pressed(9) || pressed(3)) this.emit('menu');
      if (pressed(12)) this.emit('up');
      if (pressed(13)) this.emit('down');
      if (pressed(14)) this.emit('left');
      if (pressed(15)) this.emit('right');
      this._gp = gp.buttons.map((b) => b.pressed);
    }
    const len = Math.hypot(x, y);
    if (len > 1) { x /= len; y /= len; }
    // UI 表示中はスティックで上下選択
    if (uiBusy && this.stick) {
      const dir = Math.abs(this.move.y) > 0.6 ? (this.move.y < 0 ? 'up' : 'down') : Math.abs(this.move.x) > 0.6 ? (this.move.x < 0 ? 'left' : 'right') : null;
      this._navT -= dt;
      if (dir && (dir !== this._navDir || this._navT <= 0)) { this.emit(dir); this._navT = dir === this._navDir ? 0.16 : 0.38; }
      this._navDir = dir;
      return { x: 0, y: 0, len: 0 };
    }
    return { x, y, len: Math.min(1, len) };
  }
}
