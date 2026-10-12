import * as THREE from 'three';

const angDiff = (a, b) => { let d = (b - a) % (Math.PI * 2); if (d > Math.PI) d -= Math.PI * 2; if (d < -Math.PI) d += Math.PI * 2; return d; };
export { angDiff };

/** スキニングされた人型。Idle/Walk/Run を速度でブレンドし、単発アクションも再生する */
export class Humanoid {
  constructor(lib, model) {
    const h = lib.humanoid(model);
    this.root = h.root;
    this.mixer = h.mixer;
    this.actions = h.actions;
    this.parts = h.parts;
    this.speed = 0;
    this.heading = 0;
    this.oneShot = null;
    for (const k of ['Idle', 'Walk', 'Run']) {
      const a = this.actions[k];
      if (!a) continue;
      a.play();
      a.setEffectiveWeight(k === 'Idle' ? 1 : 0);
    }
    if (this.actions.Idle) this.actions.Idle.time = Math.random() * 2;
    this.setWeapon(false);
  }

  setWeapon(drawn) {
    if (this.parts.Sword) this.parts.Sword.visible = drawn;
    if (this.parts.Sheath) this.parts.Sheath.visible = !drawn;
  }

  /** 単発アクション（Attack, Cast, Hurt, Victory, Down, Talk） */
  play(name, { loop = false, fade = 0.12, hold = false, timeScale = 1 } = {}) {
    const a = this.actions[name];
    if (!a) return Promise.resolve();
    if (this.oneShot && this.oneShot !== a) this.oneShot.fadeOut(fade);
    a.reset();
    a.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
    a.clampWhenFinished = hold;
    a.timeScale = timeScale;
    a.setEffectiveWeight(1);
    a.fadeIn(fade).play();
    this.oneShot = a;
    return new Promise((res) => {
      if (loop) return res();
      const dur = a.getClip().duration / timeScale;
      setTimeout(() => { if (!hold && this.oneShot === a) { a.fadeOut(0.2); this.oneShot = null; } res(); }, dur * 1000);
    });
  }

  stopOneShot(fade = 0.25) {
    if (this.oneShot) { this.oneShot.fadeOut(fade); this.oneShot = null; }
  }

  update(dt) {
    const s = this.speed;
    const A = this.actions;
    const wWalk = THREE.MathUtils.clamp(s / 1.6, 0, 1) * (1 - THREE.MathUtils.clamp((s - 3.2) / 1.6, 0, 1));
    const wRun = THREE.MathUtils.clamp((s - 3.2) / 1.6, 0, 1);
    const wIdle = 1 - Math.max(wWalk, wRun);
    const one = this.oneShot ? this.oneShot.getEffectiveWeight() : 0;
    const k = 1 - one;
    if (A.Idle) A.Idle.setEffectiveWeight(wIdle * k);
    if (A.Walk) { A.Walk.setEffectiveWeight(wWalk * k); A.Walk.timeScale = Math.max(0.5, s / 1.45); }
    if (A.Run) { A.Run.setEffectiveWeight(wRun * k); A.Run.timeScale = Math.max(0.7, s / 4.6); }
    this.mixer.update(dt);
  }
}

/** モンスター：種類ごとの手続き的アニメーション */
export class Monster {
  constructor(lib, def) {
    const m = lib.monster(def.model, def.recolor);
    this.def = def;
    this.root = m.root;
    this.parts = m.parts;
    this.mats = m.mats;
    this.kind = def.model.replace('Mon_', '');
    this.t = Math.random() * 10;
    this.speed = 0;
    this.flash = 0;
    this.lunge = 0;
    this.dead = false;
    this.opacity = 1;
    this.root.scale.setScalar(def.scale || 1);
    this.body = this.parts.Body;
    this.baseY = 0;
  }

  hitFlash() { this.flash = 1; }

  setOpacity(v) {
    this.opacity = v;
    for (const m of this.mats) { m.transparent = v < 1; m.opacity = v; m.depthWrite = v > 0.5; }
  }

  update(dt) {
    this.t += dt * (1 + this.speed * 0.25);
    const t = this.t, P = this.parts;
    const rest = (o) => o && o.userData.rest;
    const b = this.body;
    if (b && rest(b)) {
      b.position.copy(rest(b).p);
      b.rotation.copy(rest(b).r);
      b.scale.copy(rest(b).s);
    }
    switch (this.kind) {
      case 'Purun': {
        const hop = Math.abs(Math.sin(t * 3.2));
        const sq = 1 - hop * 0.18 + 0.1 * (1 - hop);
        b.scale.set(1 / Math.sqrt(sq), sq, 1 / Math.sqrt(sq));
        b.position.y += hop * (0.15 + this.speed * 0.06);
        break;
      }
      case 'Bat': {
        const f = Math.sin(t * 14);
        if (P.WingL) P.WingL.rotation.z = rest(P.WingL).r.z + f * 0.9;
        if (P.WingR) P.WingR.rotation.z = rest(P.WingR).r.z - f * 0.9;
        const y = Math.sin(t * 2.4) * 0.15 + f * 0.04;
        b.position.y += y;
        if (P.WingL) P.WingL.position.y = rest(P.WingL).p.y + y;
        if (P.WingR) P.WingR.position.y = rest(P.WingR).p.y + y;
        break;
      }
      case 'Mushroom': {
        b.rotation.z = Math.sin(t * 4) * 0.12;
        b.position.y += Math.abs(Math.sin(t * 4)) * 0.08;
        break;
      }
      case 'Ghost': {
        b.position.y += Math.sin(t * 1.6) * 0.18;
        b.rotation.z = Math.sin(t * 1.1) * 0.12;
        b.rotation.y = Math.sin(t * 0.7) * 0.2;
        break;
      }
      case 'Golem': {
        const s = Math.sin(t * 2.2);
        b.position.y += Math.abs(s) * 0.05;
        b.rotation.z = s * 0.04;
        if (P.ArmL) P.ArmL.rotation.x = rest(P.ArmL).r.x + s * 0.3;
        if (P.ArmR) P.ArmR.rotation.x = rest(P.ArmR).r.x - s * 0.3;
        break;
      }
      case 'Dragon': {
        const br = Math.sin(t * 1.3);
        b.scale.set(1 + br * 0.015, 1 + br * 0.02, 1 + br * 0.015);
        if (P.WingL) P.WingL.rotation.z = rest(P.WingL).r.z + Math.sin(t * 2.2) * 0.35 - 0.1;
        if (P.WingR) P.WingR.rotation.z = rest(P.WingR).r.z - Math.sin(t * 2.2) * 0.35 + 0.1;
        if (P.Head) {
          P.Head.rotation.x = rest(P.Head).r.x + Math.sin(t * 0.9) * 0.08 + this.lunge * 0.5;
          P.Head.rotation.y = rest(P.Head).r.y + Math.sin(t * 0.6) * 0.15;
        }
        break;
      }
      default: break;
    }
    if (this.flash > 0) {
      this.flash = Math.max(0, this.flash - dt * 5);
      for (const m of this.mats) m.emissive.copy(m.userData.baseEmissive).lerp(new THREE.Color(1, 1, 1), this.flash);
    }
  }
}
