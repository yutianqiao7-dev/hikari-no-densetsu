/**
 * ドラクエ風 UI（白枠ウィンドウ）。モーダルはスタックで管理し、入力は最前面に渡す。
 */
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

export class UI {
  constructor(root, audio) {
    this.root = root;
    this.audio = audio;
    this.stack = [];
    this.textSpeed = 28; // 文字/秒 ×  …
    for (const id of ['fade', 'flash', 'swirl']) { const d = el('div'); d.id = id; root.appendChild(d); this[id] = d; }
    this.banner = el('div'); this.banner.id = 'area-banner'; root.appendChild(this.banner);
  }

  get busy() { return this.stack.length > 0; }
  top() { return this.stack[this.stack.length - 1]; }
  key(k) { const t = this.top(); if (t && t.key) t.key(k); }
  push(m) { this.stack.push(m); }
  pop(m) { const i = this.stack.indexOf(m); if (i >= 0) this.stack.splice(i, 1); }

  // -------------------------------------------------------------- メッセージ
  /** lines: [{who, text, se, action}] / 文字列 */
  async say(lines, opts = {}) {
    if (!Array.isArray(lines)) lines = [lines];
    const w = el('div', 'win');
    w.id = 'msg';
    this.root.appendChild(w);
    for (const ln of lines) {
      const line = typeof ln === 'string' ? { text: ln } : ln;
      if (line.se) this.audio.sfx(line.se);
      if (line.action && opts.onAction) await opts.onAction(line.action);
      await this.typeLine(w, line, opts);
    }
    if (!opts.keep) w.remove();
    return w;
  }

  typeLine(w, line, opts) {
    return new Promise((resolve) => {
      w.innerHTML = '';
      if (line.who) w.appendChild(el('div', 'speaker', line.who));
      const body = el('div');
      w.appendChild(body);
      const text = line.text;
      let i = 0, done = false, timer;
      const finish = () => { clearInterval(timer); body.textContent = text; done = true; if (!opts.auto) w.appendChild(el('div', 'next', '▼')); };
      const m = {
        key: (k) => {
          if (k !== 'confirm' && k !== 'cancel') return;
          if (!done) { finish(); return; }
          this.pop(m);
          this.audio.sfx('cursor');
          resolve();
        },
      };
      this.push(m);
      timer = setInterval(() => {
        i += 1;
        body.textContent = text.slice(0, i);
        if (i % 2 === 0 && text[i - 1] !== ' ') this.audio.sfx('text');
        if (i >= text.length) {
          finish();
          if (opts.auto) { setTimeout(() => { this.pop(m); resolve(); }, opts.auto); }
        }
      }, 1000 / (opts.speed || this.textSpeed * 1.4));
      w.onpointerup = () => m.key('confirm');
    });
  }

  /** 戦闘用の常駐メッセージ（自動で進む） */
  battleLog() {
    const w = el('div', 'win');
    w.id = 'msg';
    this.root.appendChild(w);
    const log = {
      el: w,
      lines: [],
      set: (t) => { log.lines = [t]; w.textContent = t; },
      add: async (t, hold = 520) => {
        log.lines.push(t);
        if (log.lines.length > 3) log.lines.shift();
        const prev = log.lines.slice(0, -1).join('\n');
        for (let i = 1; i <= t.length; i++) {
          w.textContent = (prev ? prev + '\n' : '') + t.slice(0, i);
          if (i % 2 === 0) this.audio.sfx('text');
          await wait(16);
        }
        await wait(hold);
      },
      clear: () => { log.lines = []; w.textContent = ''; },
      remove: () => w.remove(),
    };
    return log;
  }

  // -------------------------------------------------------------- 選択肢
  /**
   * items: [{label, sub, disabled, desc}]  → 選んだ index（キャンセル -1）
   */
  choose(items, { id, x, y, right, bottom, title, grid = false, cancel = true, start = 0, keep = false, onMove } = {}) {
    return new Promise((resolve) => {
      const w = el('div', 'win menu' + (grid ? ' grid' : ''));
      if (id) w.id = id;
      if (title) w.appendChild(el('div', 'title', title));
      const pos = (k, v) => { if (v != null) w.style[k] = typeof v === 'number' ? v + 'px' : v; };
      pos('left', x); pos('top', y); pos('right', right); pos('bottom', bottom);
      const rows = items.map((it, i) => {
        const r = el('div', 'item' + (it.disabled ? ' disabled' : ''));
        r.appendChild(el('span', '', it.label));
        if (it.sub != null) r.appendChild(el('span', 'sub', it.sub));
        r.onpointerenter = (e) => { if (e.pointerType === 'mouse') setSel(i); };
        r.onpointerup = (e) => { e.stopPropagation(); setSel(i, true); m.key('confirm'); };
        w.appendChild(r);
        return r;
      });
      const desc = el('div', 'desc');
      if (items.some((it) => it.desc)) w.appendChild(desc);
      this.root.appendChild(w);
      let sel = Math.min(start, items.length - 1);
      const setSel = (i, silent) => {
        if (i === sel && rows[i].classList.contains('sel')) return;
        rows.forEach((r) => r.classList.remove('sel'));
        sel = (i + items.length) % items.length;
        rows[sel].classList.add('sel');
        desc.textContent = items[sel].desc || '';
        if (!silent) this.audio.sfx('cursor');
        if (onMove) onMove(sel);
      };
      setSel(sel, true);
      const close = (v) => { this.pop(m); if (!keep) w.remove(); else w.style.opacity = 0.6; resolve(v); };
      const cols = grid ? 2 : 1;
      const m = {
        el: w,
        key: (k) => {
          if (k === 'up') setSel(sel - cols);
          else if (k === 'down') setSel(sel + cols);
          else if (k === 'left' && grid) setSel(sel - 1);
          else if (k === 'right' && grid) setSel(sel + 1);
          else if (k === 'confirm') {
            if (items[sel].disabled) { this.audio.sfx('cancel'); return; }
            this.audio.sfx('confirm');
            close(sel);
          } else if (k === 'cancel' && cancel) { this.audio.sfx('cancel'); close(-1); }
        },
      };
      m.close = () => { this.pop(m); w.remove(); };
      w.menu = m;
      this.push(m);
    });
  }

  yesno(opts = {}) {
    return this.choose([{ label: 'はい' }, { label: 'いいえ' }], { right: 'calc(14px + var(--sar) + var(--btnw))', bottom: 'calc(7.6em + var(--sab))', ...opts })
      .then((i) => i === 0);
  }

  window(html, opts = {}) {
    const w = el('div', 'win', html);
    if (opts.id) w.id = opts.id;
    this.root.appendChild(w);
    return w;
  }

  /** 何かキーが押されるまで待つ（ステータス画面など） */
  /** ボタンかタップで進む。w があればそのウィンドウを、なければ画面のどこをタップしても進む */
  waitKey(w, { indicator } = {}) {
    return new Promise((resolve) => {
      let veil = null, mark = null;
      const m = {
        key: (k) => {
          if (k !== 'confirm' && k !== 'cancel') return;
          this.pop(m);
          this.audio.sfx('cursor');
          if (w) w.remove();
          if (veil) veil.remove();
          if (mark) mark.remove();
          resolve();
        },
      };
      if (w) w.onpointerup = () => m.key('confirm');
      else {
        veil = el('div');
        veil.style.cssText = 'position:absolute;inset:0;pointer-events:auto;z-index:5';
        veil.addEventListener('pointerup', (e) => { e.preventDefault(); m.key('confirm'); });
        this.root.appendChild(veil);
      }
      if (indicator) { mark = el('div', 'next', '▼'); indicator.appendChild(mark); }
      this.push(m);
    });
  }

  /** 名前入力 */
  askName(def) {
    return new Promise((resolve) => {
      const w = el('div', 'win');
      w.style.cssText = 'left:50%;top:40%;transform:translate(-50%,-50%);min-width:15em;text-align:center';
      w.innerHTML = '<div style="margin-bottom:.5em">ゆうしゃの なまえを きめてください</div>';
      const inp = el('input');
      inp.maxLength = 6;
      inp.value = def;
      inp.style.cssText = 'font:inherit;font-size:1.2em;width:8em;text-align:center;background:#000;color:#fff;border:2px solid #fff;border-radius:6px;padding:.2em';
      w.appendChild(inp);
      const ok = el('div', 'win menu', '<div class="item sel">けってい</div>');
      ok.style.cssText = 'position:relative;display:inline-block;margin-top:.8em';
      w.appendChild(el('br'));
      w.appendChild(ok);
      this.root.appendChild(w);
      const m = { key: (k) => { if (k === 'confirm') done(); } };
      const done = () => { this.pop(m); const v = (inp.value || def).trim().slice(0, 6) || def; w.remove(); this.audio.sfx('confirm'); resolve(v); };
      ok.onpointerup = done;
      inp.onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); done(); } e.stopPropagation(); };
      this.push(m);
      setTimeout(() => inp.focus(), 50);
    });
  }

  // -------------------------------------------------------------- 画面効果
  fadeTo(v, ms = 500) {
    this.fade.style.transition = `opacity ${ms}ms`;
    this.fade.style.opacity = v;
    return wait(ms);
  }
  flashScreen(color = '#fff', ms = 160, peak = 0.85) {
    const f = this.flash;
    f.style.background = color;
    f.style.transition = 'none';
    f.style.opacity = peak;
    requestAnimationFrame(() => { f.style.transition = `opacity ${ms}ms`; f.style.opacity = 0; });
  }
  async swirlIn() {
    this.swirl.classList.remove('go');
    void this.swirl.offsetWidth;
    this.swirl.classList.add('go');
    await wait(900);
  }
  swirlOut() { this.swirl.classList.remove('go'); this.swirl.style.opacity = 0; }

  showBanner(text) {
    this.banner.textContent = text;
    this.banner.classList.add('show');
    clearTimeout(this._bt);
    this._bt = setTimeout(() => this.banner.classList.remove('show'), 2600);
  }

  popup(x, y, text, cls = '') {
    const d = el('div', 'dmg ' + cls, text);
    d.style.left = x + 'px';
    d.style.top = y + 'px';
    this.root.appendChild(d);
    setTimeout(() => d.remove(), 1150);
  }
}
