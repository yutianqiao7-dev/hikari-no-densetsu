import * as THREE from 'three';

const angDiff = (a, b) => { let d = (b - a) % (Math.PI * 2); if (d > Math.PI) d -= Math.PI * 2; if (d < -Math.PI) d += Math.PI * 2; return d; };
export { angDiff };

/** スキニングされた人型。Idle/Walk/Run を速度でブレンドし、単発アクションも再生する */
const HOLD_BEND = 1.2; // blender/build_characters.py と同じ

export class Humanoid {
  constructor(lib, model) {
    const h = lib.humanoid(model);
    this.outlinePairs = h.outlinePairs || [];
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
    if (['Staff', 'Axe', 'Spear'].some((k) => this.parts[k])) this.setupHold();
    // まばたき・口の形（Blender の形のキー）
    this.morphs = [];
    this.root.traverse((o) => {
      const d = o.morphTargetDictionary;
      if (o.isMesh && d && !o.userData.isOutline) this.morphs.push({ o, blink: d.Blink, talk: d.Talk });
    });
    this.blinkT = 1 + Math.random() * 3;
    this.blinkA = -1;
    this.mouth = 0;
    this.speaking = false;
  }

  /** まばたき（2〜5 秒おき、ときどき 2 回続けて）と、話しているあいだの口 */
  updateFace(dt) {
    if (!this.morphs.length) return;
    let blink = 0;
    if (this.blinkA >= 0) {
      this.blinkA += dt;
      const t = this.blinkA / 0.15;
      blink = t < 1 ? Math.sin(t * Math.PI) : 0;
      if (t >= 1) { this.blinkA = -1; this.blinkT = Math.random() < 0.2 ? 0.12 : 2 + Math.random() * 3; }
    } else if ((this.blinkT -= dt) <= 0) this.blinkA = 0;
    this.faceT = (this.faceT || 0) + dt;
    const target = this.speaking ? 0.35 + 0.65 * Math.abs(Math.sin(this.faceT * 13) * Math.sin(this.faceT * 7.3 + 1)) : 0;
    this.mouth += (target - this.mouth) * Math.min(1, dt * 18);
    for (const m of this.morphs) {
      const inf = m.o.morphTargetInfluences;
      if (m.blink !== undefined) inf[m.blink] = blink;
      if (m.talk !== undefined) inf[m.talk] = this.mouth;
    }
  }

  /**
   * 杖・斧・槍を持つキャラは、右ひじを前に曲げて柄を縦に握る（Blender 側の HOLD_BEND と同じ角度）。
   * 共通のアニメーションのあとに、ひじの曲げを毎フレーム足す。
   */
  setupHold() {
    let fa = null, hand = null;
    this.root.traverse((o) => {
      if (!o.isBone) return;
      if (!fa && /^forearmR/.test(o.name)) fa = o;
      if (!hand && /^handR/.test(o.name)) hand = o;
    });
    if (!fa || !hand) return;
    this.root.updateMatrixWorld(true);
    const e = fa.getWorldPosition(new THREE.Vector3()), w = hand.getWorldPosition(new THREE.Vector3());
    const ax = w.sub(e).normalize().cross(new THREE.Vector3(0, 0, -1)).normalize();
    const qW = new THREE.Quaternion().setFromAxisAngle(ax, -HOLD_BEND);
    const wr = fa.getWorldQuaternion(new THREE.Quaternion());
    this.holdQ = wr.clone().invert().multiply(qW).multiply(wr);
    this.holdBone = fa;
    this.holdBase = fa.quaternion.clone();
  }

  setWeapon(drawn) {
    if (this.parts.Sword) this.parts.Sword.visible = drawn;
    if (this.parts.Sheath) this.parts.Sheath.visible = !drawn;
  }

  /** 単発アクション（Attack, Cast, Hurt, Victory, Down, Talk） */
  has(name) { return !!this.actions[name]; }

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
    // ミキサーは値が変わらないフレームでは骨を書きかえないので、足した曲げを先に取りのぞく（でないと積み重なって回る）
    const hb = this.holdBone;
    if (hb) hb.quaternion.copy(this.holdBase);
    this.mixer.update(dt);
    for (const [a, b] of this.outlinePairs) b.visible = a.visible;
    this.updateFace(dt);
    if (hb) { this.holdBase.copy(hb.quaternion); hb.quaternion.multiply(this.holdQ); }
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
    this.outlineMats = m.outlineMats || [];
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
    // 竜の鞍は乗るときだけ
    if (this.parts.Saddle) this.parts.Saddle.visible = false;
  }

  hitFlash() { this.flash = 1; }

  setOpacity(v) {
    this.opacity = v;
    for (const m of this.mats) { m.transparent = v < 1; m.opacity = v; m.depthWrite = v > 0.5; }
    for (const m of this.outlineMats) m.visible = v > 0.97;
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
      case 'Wolf': {
        const amp = Math.min(0.55, 0.12 + this.speed * 0.09 + Math.abs(this.lunge) * 0.3);
        const s = Math.sin(t * (5 + this.speed * 0.6));
        const sw = (o, v) => { if (o) o.rotation.x = rest(o).r.x + v; };
        sw(P.LegFL, s * amp); sw(P.LegBR, s * amp);
        sw(P.LegFR, -s * amp); sw(P.LegBL, -s * amp);
        b.position.y += Math.abs(Math.cos(t * (5 + this.speed * 0.6))) * 0.035 * (amp / 0.3);
        if (P.Head) {
          P.Head.rotation.x = rest(P.Head).r.x + Math.sin(t * 1.4) * 0.06 + this.lunge * 0.45;
          P.Head.rotation.y = rest(P.Head).r.y + Math.sin(t * 0.8) * 0.15;
        }
        if (P.Tail) P.Tail.rotation.y = rest(P.Tail).r.y + Math.sin(t * 7) * 0.35;
        break;
      }
      case 'Crab': {
        const s = Math.sin(t * 6);
        b.position.y += Math.abs(s) * 0.02;
        b.rotation.z = s * 0.04;
        if (P.LegsL) P.LegsL.rotation.x = rest(P.LegsL).r.x + s * 0.14;
        if (P.LegsR) P.LegsR.rotation.x = rest(P.LegsR).r.x - s * 0.14;
        const raise = 0.12 + 0.1 * Math.sin(t * 2.1) + this.lunge * 0.5;
        if (P.ClawL) P.ClawL.rotation.x = rest(P.ClawL).r.x - raise;
        if (P.ClawR) P.ClawR.rotation.x = rest(P.ClawR).r.x - raise * 0.8;
        const snap = Math.max(0, Math.sin(t * 3.3)) * 0.45;
        if (P.PincerL) P.PincerL.rotation.x = rest(P.PincerL).r.x - snap;
        if (P.PincerR) P.PincerR.rotation.x = rest(P.PincerR).r.x - Math.max(0, Math.sin(t * 3.3 + 1.5)) * 0.45;
        break;
      }
      case 'Stump': {
        const s = Math.sin(t * 3.6);
        b.position.y += Math.abs(s) * 0.1;
        b.rotation.z = s * 0.06;
        if (P.ArmL) P.ArmL.rotation.z = rest(P.ArmL).r.z + Math.sin(t * 3.6) * 0.3 - this.lunge * 0.6;
        if (P.ArmR) P.ArmR.rotation.z = rest(P.ArmR).r.z - Math.sin(t * 3.6 + 0.8) * 0.3 + this.lunge * 0.6;
        break;
      }
      case 'Skeleton': {
        const amp = Math.min(0.5, 0.12 + this.speed * 0.07);
        const s = Math.sin(t * 4.2);
        b.position.y += Math.abs(Math.cos(t * 4.2)) * 0.03;
        b.rotation.z = Math.sin(t * 2.1) * 0.03;
        if (P.LegL) P.LegL.rotation.x = rest(P.LegL).r.x + s * amp;
        if (P.LegR) P.LegR.rotation.x = rest(P.LegR).r.x - s * amp;
        if (P.ArmL) P.ArmL.rotation.x = rest(P.ArmL).r.x - s * amp * 0.5;
        if (P.ArmR) P.ArmR.rotation.x = rest(P.ArmR).r.x + s * amp * 0.5 - this.lunge * 1.3;
        if (P.Head) {
          P.Head.rotation.z = rest(P.Head).r.z + Math.sin(t * 1.7) * 0.1 + Math.sin(t * 23) * 0.015;
          P.Head.rotation.y = rest(P.Head).r.y + Math.sin(t * 0.9) * 0.2;
        }
        break;
      }
      case 'Wisp': {
        const y = Math.sin(t * 2) * 0.15;
        b.position.y += y;
        b.scale.set(1 + Math.sin(t * 13) * 0.04, 1 + Math.sin(t * 17 + 1) * 0.07, 1 + Math.sin(t * 11) * 0.04);
        b.rotation.y = Math.sin(t * 0.9) * 0.3;
        if (P.Embers) { P.Embers.rotation.y = t * 1.5; P.Embers.position.y = rest(P.Embers).p.y + y * 0.6; }
        break;
      }
      case 'Snake': {
        if (P.Neck) {
          P.Neck.rotation.z = rest(P.Neck).r.z + Math.sin(t * 1.8) * 0.12;
          P.Neck.rotation.x = rest(P.Neck).r.x + Math.sin(t * 1.3) * 0.06 + this.lunge * 0.55;
        }
        if (P.Head) P.Head.rotation.y = rest(P.Head).r.y + Math.sin(t * 2.2) * 0.18;
        const br = Math.sin(t * 1.5);
        b.scale.set(1 + br * 0.015, 1 + br * 0.01, 1 + br * 0.015);
        break;
      }
      case 'Gargoyle': {
        const f = Math.sin(t * 6);
        const y = Math.sin(t * 2) * 0.12 + f * 0.03;
        b.position.y += y;
        b.rotation.x = 0.08 + this.lunge * 0.4;
        for (const [o, sgn] of [[P.WingL, 1], [P.WingR, -1]]) {
          if (!o) continue;
          o.rotation.z = rest(o).r.z + sgn * (f * 0.6 + 0.1);
          o.position.y = rest(o).p.y + y;
        }
        break;
      }
      case 'Scorpion': {
        const s = Math.sin(t * 7);
        b.position.y += Math.abs(s) * 0.015;
        if (P.LegsL) P.LegsL.rotation.x = rest(P.LegsL).r.x + s * 0.15;
        if (P.LegsR) P.LegsR.rotation.x = rest(P.LegsR).r.x - s * 0.15;
        if (P.Tail) {
          P.Tail.rotation.x = rest(P.Tail).r.x + Math.sin(t * 1.7) * 0.08 + this.lunge * 0.7;
          P.Tail.rotation.z = rest(P.Tail).r.z + Math.sin(t * 1.1) * 0.1;
        }
        const raise = 0.1 + 0.08 * Math.sin(t * 2.3) + this.lunge * 0.4;
        if (P.ClawL) P.ClawL.rotation.x = rest(P.ClawL).r.x - raise;
        if (P.ClawR) P.ClawR.rotation.x = rest(P.ClawR).r.x - raise;
        if (P.PincerL) P.PincerL.rotation.x = rest(P.PincerL).r.x - Math.max(0, Math.sin(t * 3)) * 0.45;
        if (P.PincerR) P.PincerR.rotation.x = rest(P.PincerR).r.x - Math.max(0, Math.sin(t * 3 + 1.4)) * 0.45;
        break;
      }
      case 'Mummy':
      case 'Anubis':
      case 'DarkKnight': {
        const slow = this.kind === 'Mummy' ? 2.4 : this.kind === 'Anubis' ? 3.0 : 3.6;
        const amp = Math.min(0.45, (this.kind === 'Mummy' ? 0.1 : 0.12) + this.speed * 0.06);
        const s = Math.sin(t * slow);
        b.position.y += Math.abs(Math.cos(t * slow)) * 0.025;
        b.rotation.z = Math.sin(t * slow * 0.5) * (this.kind === 'Mummy' ? 0.06 : 0.025);
        if (P.LegL) P.LegL.rotation.x = rest(P.LegL).r.x + s * amp;
        if (P.LegR) P.LegR.rotation.x = rest(P.LegR).r.x - s * amp;
        if (this.kind === 'Mummy') {
          if (P.ArmL) P.ArmL.rotation.x = rest(P.ArmL).r.x + Math.sin(t * 1.3) * 0.08 - this.lunge * 0.4;
          if (P.ArmR) P.ArmR.rotation.x = rest(P.ArmR).r.x + Math.sin(t * 1.3 + 1) * 0.08 - this.lunge * 0.4;
          if (P.Head) P.Head.rotation.z = rest(P.Head).r.z + Math.sin(t * 0.8) * 0.15;
        } else {
          if (P.ArmL) P.ArmL.rotation.x = rest(P.ArmL).r.x - s * amp * 0.5;
          if (P.ArmR) P.ArmR.rotation.x = rest(P.ArmR).r.x + s * amp * 0.5 - this.lunge * 1.2;
          if (P.Head) P.Head.rotation.y = rest(P.Head).r.y + Math.sin(t * 0.7) * 0.18;
          if (P.Cape) P.Cape.rotation.x = rest(P.Cape).r.x + 0.08 + Math.sin(t * 1.6) * 0.06 + this.speed * 0.04;
        }
        break;
      }
      case 'Cactus':
      case 'Snowman': {
        const f = this.kind === 'Cactus' ? 3.4 : 2.6;
        const s = Math.sin(t * f);
        b.position.y += Math.abs(s) * (this.kind === 'Cactus' ? 0.12 : 0.06);
        b.rotation.z = s * 0.07;
        if (P.ArmL) P.ArmL.rotation.z = rest(P.ArmL).r.z + Math.sin(t * f) * 0.25 - this.lunge * 0.5;
        if (P.ArmR) P.ArmR.rotation.z = rest(P.ArmR).r.z - Math.sin(t * f + 0.7) * 0.25 + this.lunge * 0.5;
        if (P.Head) P.Head.rotation.z = rest(P.Head).r.z + Math.sin(t * 1.3) * 0.12;
        break;
      }
      case 'Penguin': {
        const s = Math.sin(t * 6);
        b.rotation.z = s * 0.14;
        b.position.y += Math.abs(s) * 0.04;
        if (P.ArmL) P.ArmL.rotation.z = rest(P.ArmL).r.z + (0.25 + 0.25 * Math.sin(t * 9)) ;
        if (P.ArmR) P.ArmR.rotation.x = rest(P.ArmR).r.x - this.lunge * 1.2 + Math.sin(t * 2) * 0.05;
        break;
      }
      case 'Yeti': {
        const s = Math.sin(t * 2.2);
        b.position.y += Math.abs(s) * 0.05;
        b.rotation.z = s * 0.05;
        if (P.ArmL) P.ArmL.rotation.x = rest(P.ArmL).r.x + s * 0.3 - this.lunge * 0.8;
        if (P.ArmR) P.ArmR.rotation.x = rest(P.ArmR).r.x - s * 0.3 - this.lunge * 0.8;
        break;
      }
      case 'Lizard': {
        const amp = Math.min(0.5, 0.15 + this.speed * 0.08);
        const s = Math.sin(t * (6 + this.speed * 0.5));
        const sw = (o, v) => { if (o) o.rotation.y = rest(o).r.y + v; };
        sw(P.LegFL, s * amp); sw(P.LegBR, s * amp); sw(P.LegFR, s * amp); sw(P.LegBL, s * amp);
        b.rotation.y = s * 0.08;
        if (P.Tail) P.Tail.rotation.y = rest(P.Tail).r.y - s * 0.25;
        if (P.Head) P.Head.rotation.x = rest(P.Head).r.x + Math.sin(t * 1.5) * 0.06 + this.lunge * 0.5;
        if (P.Flame) P.Flame.scale.set(1 + Math.sin(t * 13) * 0.12, 1 + Math.sin(t * 17) * 0.18, 1 + Math.sin(t * 11) * 0.12);
        break;
      }
      case 'Firebird': {
        const f = Math.sin(t * 5);
        const y = Math.sin(t * 1.8) * 0.15 + f * 0.04;
        b.position.y += y;
        for (const [o, sgn] of [[P.WingL, 1], [P.WingR, -1]]) {
          if (!o) continue;
          o.rotation.z = rest(o).r.z + sgn * f * 0.65;
          o.position.y = rest(o).p.y + y;
        }
        if (P.Tail) { P.Tail.position.y = rest(P.Tail).p.y + y; P.Tail.rotation.x = rest(P.Tail).r.x + Math.sin(t * 2.3) * 0.12; }
        break;
      }
      case 'Ifrit': {
        const y = Math.sin(t * 1.4) * 0.18;
        b.position.y += y;
        if (P.ArmL) P.ArmL.rotation.x = rest(P.ArmL).r.x + Math.sin(t * 1.4) * 0.15 - this.lunge * 0.9;
        if (P.ArmR) P.ArmR.rotation.x = rest(P.ArmR).r.x + Math.sin(t * 1.4 + 1) * 0.15 - this.lunge * 0.9;
        if (P.Head) P.Head.rotation.x = rest(P.Head).r.x + Math.sin(t * 0.9) * 0.06 + this.lunge * 0.3;
        if (P.Flame) { P.Flame.rotation.y = t * 1.5; P.Flame.scale.set(1 + Math.sin(t * 9) * 0.05, 1 + Math.sin(t * 13) * 0.08, 1 + Math.sin(t * 9) * 0.05); }
        if (P.Hair) P.Hair.scale.set(1, 1 + Math.sin(t * 15) * 0.12, 1);
        break;
      }
      case 'EvilEye': {
        const f = Math.sin(t * 11);
        const y = Math.sin(t * 2) * 0.15;
        b.position.y += y;
        b.rotation.y = Math.sin(t * 0.9) * 0.25;
        b.rotation.x = this.lunge * 0.4;
        for (const [o, sgn] of [[P.WingL, 1], [P.WingR, -1]]) {
          if (!o) continue;
          o.rotation.z = rest(o).r.z + sgn * f * 0.7;
          o.position.y = rest(o).p.y + y;
        }
        if (P.Tentacles) { P.Tentacles.position.y = rest(P.Tentacles).p.y + y; P.Tentacles.rotation.y = Math.sin(t * 1.3) * 0.4; P.Tentacles.rotation.x = Math.sin(t * 1.7) * 0.1; }
        break;
      }
      case 'Zenos': {
        const y = Math.sin(t * 1.1) * 0.2;
        b.position.y += y;
        const fl = Math.sin(t * 1.6);
        for (const [o, sgn] of [[P.WingL, 1], [P.WingR, -1]]) {
          if (!o) continue;
          o.rotation.z = rest(o).r.z + sgn * (fl * 0.25 + 0.05);
          o.position.y = rest(o).p.y + y;
        }
        if (P.ArmR) P.ArmR.rotation.x = rest(P.ArmR).r.x - this.lunge * 1.0 + Math.sin(t * 0.8) * 0.06;
        if (P.ArmL) P.ArmL.rotation.x = rest(P.ArmL).r.x - this.lunge * 0.6 + Math.sin(t * 0.8 + 1) * 0.06;
        if (P.Head) P.Head.rotation.y = rest(P.Head).r.y + Math.sin(t * 0.5) * 0.15;
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
