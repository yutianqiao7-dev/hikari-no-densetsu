import * as THREE from 'three';

function puffTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  for (let i = 0; i < 9; i++) {
    const x = 20 + Math.random() * 24, y = 20 + Math.random() * 24, r = 10 + Math.random() * 14;
    const grd = g.createRadialGradient(x, y, 0, x, y, r);
    grd.addColorStop(0, 'rgba(255,255,255,0.5)');
    grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd;
    g.fillRect(0, 0, 64, 64);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** 煙突の煙と、夜に灯る街灯の光 */
export class Ambience {
  constructor(scene, world, q) {
    this.scene = scene;
    this.world = world;
    const mk = world.markers;
    this.smokers = Object.entries(mk).filter(([k]) => k.startsWith('Smoke_')).map(([, m]) => new THREE.Vector3(m.x, m.y, m.z));
    this.lamps = Object.entries(mk).filter(([k]) => k.startsWith('Light_')).map(([, m]) => new THREE.Vector3(m.x, m.y, m.z));

    // 煙（通常合成のパーティクル）
    const max = 600;
    this.max = max;
    this.pos = new Float32Array(max * 3);
    this.size = new Float32Array(max);
    this.alpha = new Float32Array(max);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    geo.setAttribute('size', new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    geo.setAttribute('alpha', new THREE.BufferAttribute(this.alpha, 1).setUsage(THREE.DynamicDrawUsage));
    geo.setDrawRange(0, 0);
    this.geo = geo;
    this.mat = new THREE.ShaderMaterial({
      uniforms: { map: { value: puffTexture() }, uScale: { value: 600 }, uColor: { value: new THREE.Color(0.8, 0.8, 0.82) } },
      transparent: true, depthWrite: false,
      vertexShader: /* glsl */`
        attribute float size; attribute float alpha; varying float vA; uniform float uScale;
        void main() { vA = alpha; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_PointSize = size * uScale / max(-mv.z, 0.1); gl_Position = projectionMatrix * mv; }`,
      fragmentShader: /* glsl */`
        uniform sampler2D map; uniform vec3 uColor; varying float vA;
        void main() { vec4 t = texture2D(map, gl_PointCoord); gl_FragColor = vec4(uColor, t.a * vA); }`,
    });
    const pts = new THREE.Points(geo, this.mat);
    pts.frustumCulled = false;
    pts.renderOrder = 5;
    scene.add(pts);
    this.parts = [];
    this.emitT = 0;

    // 街灯の光（近いものから順に割り当てる）
    const n = q.label === '最高' ? 6 : q.label === '高' ? 3 : 0;
    this.lights = [];
    for (let i = 0; i < n; i++) {
      const l = new THREE.PointLight(0xffb060, 0, 16, 1.8);
      scene.add(l);
      this.lights.push(l);
    }
    this.assignT = 0;
  }

  setViewport(h) { this.mat.uniforms.uScale.value = h * 0.9; }

  update(dt, t, cam, sky) {
    // 煙
    this.emitT -= dt;
    if (this.emitT <= 0) {
      this.emitT = 0.18;
      for (const s of this.smokers) {
        if (s.distanceToSquared(cam) > 180 * 180 || this.parts.length >= this.max) continue;
        this.parts.push({ p: s.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.3, 0, (Math.random() - 0.5) * 0.3)), age: 0, life: 6 + Math.random() * 3, s: 0.8 + Math.random() * 0.5, sp: Math.random() * 6 });
      }
    }
    let n = 0;
    for (let i = this.parts.length - 1; i >= 0; i--) {
      const q = this.parts[i];
      q.age += dt;
      if (q.age > q.life) { this.parts.splice(i, 1); continue; }
      q.p.y += dt * (1.1 - q.age * 0.06);
      q.p.x += dt * (0.5 + Math.sin(t * 0.7 + q.sp) * 0.2) * Math.min(1, q.age * 0.5);
      q.p.z += dt * (0.3 + Math.cos(t * 0.5 + q.sp) * 0.2) * Math.min(1, q.age * 0.5);
    }
    for (const q of this.parts) {
      const k = q.age / q.life;
      this.pos[n * 3] = q.p.x; this.pos[n * 3 + 1] = q.p.y; this.pos[n * 3 + 2] = q.p.z;
      this.size[n] = q.s * (1 + k * 4);
      this.alpha[n] = Math.min(1, q.age * 1.5) * (1 - k) * 0.55;
      n++;
    }
    const a = this.geo.attributes;
    a.position.needsUpdate = a.size.needsUpdate = a.alpha.needsUpdate = true;
    this.geo.setDrawRange(0, n);
    const lv = 0.2 + sky.day * 0.75;
    this.mat.uniforms.uColor.value.setRGB(0.82 * lv + 0.04, 0.82 * lv + 0.05, 0.85 * lv + 0.08);

    // 街灯
    const on = Math.max(sky.night, sky.dusk * 0.6);
    this.assignT -= dt;
    if (this.assignT <= 0 && this.lights.length) {
      this.assignT = 0.5;
      const sorted = this.lamps.map((p) => [p.distanceToSquared(cam), p]).sort((x, y) => x[0] - y[0]);
      this.lights.forEach((l, i) => {
        const e = sorted[i];
        if (e && e[0] < 90 * 90) { l.position.copy(e[1]); l.visible = true; } else l.visible = false;
      });
    }
    this.lights.forEach((l, i) => { l.intensity = on * (14 + Math.sin(t * 13 + i * 7) * 0.8 + Math.sin(t * 5.3 + i) * 0.6); });
  }
}
