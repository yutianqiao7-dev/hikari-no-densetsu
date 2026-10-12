import * as THREE from 'three';

function glowTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, 'rgba(255,255,255,1)');
  grd.addColorStop(0.25, 'rgba(255,255,255,0.75)');
  grd.addColorStop(0.6, 'rgba(255,255,255,0.18)');
  grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** 加算合成のパーティクル（CPU 更新、1 ドローコール） */
export class FX {
  constructor(scene, max = 4000) {
    this.scene = scene;
    this.max = max;
    const geo = new THREE.BufferGeometry();
    this.pos = new Float32Array(max * 3);
    this.col = new Float32Array(max * 3);
    this.size = new Float32Array(max);
    this.alpha = new Float32Array(max);
    geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    geo.setAttribute('color', new THREE.BufferAttribute(this.col, 3).setUsage(THREE.DynamicDrawUsage));
    geo.setAttribute('size', new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    geo.setAttribute('alpha', new THREE.BufferAttribute(this.alpha, 1).setUsage(THREE.DynamicDrawUsage));
    geo.setDrawRange(0, 0);
    this.geo = geo;
    const mat = new THREE.ShaderMaterial({
      uniforms: { map: { value: glowTexture() }, uScale: { value: 600 } },
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      vertexShader: /* glsl */`
        attribute float size; attribute float alpha; attribute vec3 color;
        varying vec3 vC; varying float vA; uniform float uScale;
        void main() {
          vC = color; vA = alpha;
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * uScale / max(-mv.z, 0.1);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */`
        uniform sampler2D map; varying vec3 vC; varying float vA;
        void main() { vec4 t = texture2D(map, gl_PointCoord); gl_FragColor = vec4(vC * t.rgb * vA * 4.0, t.a * vA); }`,
    });
    this.points = new THREE.Points(geo, mat);
    this.points.frustumCulled = false;
    this.points.renderOrder = 10;
    scene.add(this.points);
    this.parts = [];
    this.trails = [];
    this.light = new THREE.PointLight(0xffaa55, 0, 18, 1.6);
    scene.add(this.light);
    this.lightT = 0;
  }

  setViewport(h) { this.points.material.uniforms.uScale.value = h * 0.9; }

  emit(o) {
    const n = o.count || 20;
    for (let i = 0; i < n && this.parts.length < this.max; i++) {
      const dir = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize();
      const sp = (o.speed || 2) * (0.4 + Math.random() * 0.8);
      const v = dir.multiplyScalar(sp);
      if (o.up) v.y += o.up * (0.5 + Math.random());
      if (o.dir) v.add(o.dir.clone().multiplyScalar(0.6 + Math.random() * 0.8));
      const p = o.pos.clone();
      if (o.spread) p.add(new THREE.Vector3((Math.random() - 0.5) * o.spread, (Math.random() - 0.5) * o.spread * (o.flat ? 0.1 : 1), (Math.random() - 0.5) * o.spread));
      const c = Array.isArray(o.color) ? o.color[Math.floor(Math.random() * o.color.length)] : o.color;
      this.parts.push({
        p, v, c: new THREE.Color(c || 0xffffff), life: (o.life || 0.8) * (0.6 + Math.random() * 0.7), age: 0,
        size: (o.size || 0.3) * (0.6 + Math.random() * 0.8), g: o.gravity ?? 0, drag: o.drag ?? 1.5, grow: o.grow ?? 0,
        flicker: o.flicker || 0,
      });
    }
  }

  flashLight(pos, color, intensity = 30, dur = 0.5) {
    this.light.position.copy(pos);
    this.light.color.set(color);
    this.light.intensity = intensity;
    this.lightPeak = intensity;
    this.lightT = dur;
    this.lightDur = dur;
  }

  /** 剣の軌跡（円弧状のリボン） */
  slash(center, facing, color = 0xcfe8ff, radius = 1.6, flip = false) {
    const seg = 24;
    const geo = new THREE.BufferGeometry();
    const pos = [], uv = [], idx = [];
    for (let i = 0; i <= seg; i++) {
      const u = i / seg;
      const a = (flip ? 1 : -1) * (-1.2 + u * 2.4);
      for (const r of [radius * 0.55, radius]) {
        const x = Math.sin(a) * r, y = Math.cos(a) * r * 0.9;
        pos.push(x, y, 0);
        uv.push(u, r === radius ? 1 : 0);
      }
      if (i < seg) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
    }
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geo.setIndex(idx);
    const mat = new THREE.ShaderMaterial({
      uniforms: { uT: { value: 0 }, uC: { value: new THREE.Color(color) } },
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: /* glsl */`
        uniform float uT; uniform vec3 uC; varying vec2 vUv;
        void main() {
          float head = uT * 1.6;
          float a = smoothstep(head - 0.7, head, vUv.x) * step(vUv.x, head) * pow(vUv.y, 2.0);
          a *= 1.0 - smoothstep(0.6, 1.0, uT);
          gl_FragColor = vec4(uC * a * 5.0, a);
        }`,
    });
    const m = new THREE.Mesh(geo, mat);
    m.position.copy(center);
    m.lookAt(center.clone().add(facing));
    m.rotateZ(flip ? 0.5 : -0.5);
    m.renderOrder = 11;
    this.scene.add(m);
    this.trails.push({ m, t: 0, dur: 0.35 });
  }

  /** 稲妻 */
  bolt(from, to, color = 0xbfe4ff) {
    const pts = [];
    const n = 14;
    for (let i = 0; i <= n; i++) {
      const p = from.clone().lerp(to, i / n);
      if (i > 0 && i < n) p.add(new THREE.Vector3((Math.random() - 0.5) * 1.2, (Math.random() - 0.5) * 0.4, (Math.random() - 0.5) * 1.2));
      pts.push(p);
    }
    for (let k = 0; k < 3; k++) {
      const g = new THREE.BufferGeometry().setFromPoints(pts.map((p) => p.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.15 * k, 0, (Math.random() - 0.5) * 0.15 * k))));
      const m = new THREE.Line(g, new THREE.LineBasicMaterial({ color, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
      m.renderOrder = 12;
      this.scene.add(m);
      this.trails.push({ m, t: 0, dur: 0.28 + k * 0.05, line: true });
    }
    for (const p of pts) this.emit({ pos: p, count: 3, color: [0xffffff, color], speed: 2, life: 0.4, size: 0.5 });
  }

  update(dt) {
    let n = 0;
    const P = this.pos, Cc = this.col, S = this.size, A = this.alpha;
    for (let i = this.parts.length - 1; i >= 0; i--) {
      const q = this.parts[i];
      q.age += dt;
      if (q.age >= q.life) { this.parts.splice(i, 1); continue; }
      q.v.y -= q.g * dt;
      q.v.multiplyScalar(Math.max(0, 1 - q.drag * dt));
      q.p.addScaledVector(q.v, dt);
    }
    for (const q of this.parts) {
      const t = q.age / q.life;
      P[n * 3] = q.p.x; P[n * 3 + 1] = q.p.y; P[n * 3 + 2] = q.p.z;
      Cc[n * 3] = q.c.r; Cc[n * 3 + 1] = q.c.g; Cc[n * 3 + 2] = q.c.b;
      S[n] = q.size * (1 + q.grow * t);
      let a = Math.min(1, t * 8) * (1 - t) * (1 - t * 0.2);
      if (q.flicker) a *= 0.6 + 0.4 * Math.sin(q.age * q.flicker + n);
      A[n] = a;
      n++;
    }
    const at = this.geo.attributes;
    at.position.needsUpdate = at.color.needsUpdate = at.size.needsUpdate = at.alpha.needsUpdate = true;
    this.geo.setDrawRange(0, n);

    for (let i = this.trails.length - 1; i >= 0; i--) {
      const tr = this.trails[i];
      tr.t += dt;
      const k = tr.t / tr.dur;
      if (tr.line) tr.m.material.opacity = 1 - k;
      else tr.m.material.uniforms.uT.value = k;
      if (k >= 1) { this.scene.remove(tr.m); tr.m.geometry.dispose(); tr.m.material.dispose(); this.trails.splice(i, 1); }
    }
    if (this.lightT > 0) {
      this.lightT -= dt;
      this.light.intensity = this.lightPeak * Math.max(0, this.lightT / this.lightDur);
    } else this.light.intensity = 0;
  }
}
