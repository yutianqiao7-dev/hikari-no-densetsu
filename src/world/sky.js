import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const lerpC = (a, b, t) => a.clone().lerp(b, t);

// 時間帯ごとの色（リニア空間）
const C = (r, g, b) => new THREE.Color(r, g, b);
const FOG_DAY = C(0.56, 0.70, 0.90), FOG_DUSK = C(0.95, 0.56, 0.36), FOG_NIGHT = C(0.05, 0.075, 0.16);
const SUN_DAY = C(1.0, 0.95, 0.86), SUN_DUSK = C(1.0, 0.55, 0.28), MOON = C(0.62, 0.74, 1.0);
const HEMI_SKY_DAY = C(0.62, 0.75, 1.0), HEMI_SKY_NIGHT = C(0.36, 0.46, 0.8);
const HEMI_GND_DAY = C(0.36, 0.33, 0.22), HEMI_GND_NIGHT = C(0.14, 0.16, 0.22);

/**
 * 空・太陽・月・星・霧・環境光（IBL）と昼夜サイクル
 */
export class SkySystem {
  constructor(scene, renderer, q) {
    this.scene = scene;
    this.renderer = renderer;
    this.q = q;
    this.time = 0.30;           // 0..1 (0.25 = 日の出, 0.5 = 正午, 0.75 = 日没)
    this.dayLength = 720;       // 秒で 1 日
    this.paused = false;

    const sky = new Sky();
    sky.scale.setScalar(4000);
    sky.frustumCulled = false;
    const u = sky.material.uniforms;
    u.turbidity.value = 3.2;
    u.rayleigh.value = 1.4;
    u.mieCoefficient.value = 0.004;
    u.mieDirectionalG.value = 0.72;
    u.cloudCoverage.value = 0.42;
    u.cloudDensity.value = 0.55;
    u.cloudScale.value = 0.00022;
    u.cloudSpeed.value = 0.00003;
    u.cloudElevation.value = 0.55;
    Object.assign(u, {
      uNight: { value: 0 }, uFogColor: { value: new THREE.Color() }, uMoonDir: { value: new THREE.Vector3(0, 1, 0) },
      uSkyGain: { value: 1.0 }, uTime: { value: 0 },
    });
    sky.material.fragmentShader = sky.material.fragmentShader
      // 太陽の円盤を見上げても目がくらまない明るさに
      .replace('( 760.0 * sundisc )', '( 26.0 * sundisc )')
      .replace('void main() {', /* glsl */`
        uniform float uNight; uniform vec3 uFogColor; uniform vec3 uMoonDir; uniform float uSkyGain; uniform float uTime;
        float hash3(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
        void main() {`)
      .replace('gl_FragColor = vec4( texColor, 1.0 );', /* glsl */`
        texColor *= uSkyGain;
        // 太陽の周りのまぶしさに上限（ブルームで画面が白飛びしないように）
        float lum = dot(texColor, vec3(0.2126, 0.7152, 0.0722));
        texColor *= min(1.0, 2.4 / max(lum, 1e-4));
        vec3 nightCol = mix(vec3(0.012, 0.02, 0.05), vec3(0.002, 0.004, 0.016), smoothstep(0.0, 0.7, direction.y));
        texColor += nightCol * uNight;
        if (direction.y > 0.0) {
          vec3 sd = direction * 420.0;
          vec3 cell = floor(sd);
          float h = hash3(cell);
          if (h > 0.9955) {
            float d = length(fract(sd) - 0.5);
            float tw = 0.55 + 0.45 * sin(uTime * (2.0 + h * 3.0) + h * 400.0);
            texColor += mix(vec3(1.0, 0.85, 0.7), vec3(0.75, 0.85, 1.0), fract(h * 91.0)) * smoothstep(0.16, 0.0, d) * uNight * tw * smoothstep(0.02, 0.25, direction.y) * 2.2;
          }
          // 天の川っぽい淡い帯
          float band = exp(-pow(dot(direction, normalize(vec3(0.3, 0.5, -0.8))) * 3.2, 2.0));
          texColor += vec3(0.05, 0.06, 0.1) * band * uNight * 0.35;
        }
        float md = dot(direction, uMoonDir);
        texColor += vec3(0.85, 0.9, 1.0) * (smoothstep(0.99955, 0.99975, md) * 3.0 + pow(max(md, 0.0), 220.0) * 0.12 + pow(max(md, 0.0), 12.0) * 0.015) * uNight;
        texColor = mix(uFogColor, texColor, smoothstep(-0.03, 0.14, direction.y));
        gl_FragColor = vec4( texColor, 1.0 );`);
    sky.material.needsUpdate = true;
    this.sky = sky;
    scene.add(sky);

    // 太陽（夜は月光として使う）
    const sun = new THREE.DirectionalLight(0xffffff, 3);
    sun.castShadow = true;
    sun.shadow.mapSize.set(q.shadow, q.shadow);
    const r = q.shadowRange;
    Object.assign(sun.shadow.camera, { left: -r, right: r, top: r, bottom: -r, near: 1, far: 500 });
    sun.shadow.bias = -0.0003;
    sun.shadow.normalBias = 0.035;
    sun.shadow.radius = 2;
    scene.add(sun, sun.target);
    this.sun = sun;

    this.hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0);
    scene.add(this.hemi);

    scene.fog = new THREE.FogExp2(0x9ab, 0.0022);

    // IBL 用：空だけを描くシーン
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.envScene = new THREE.Scene();
    this.envSky = new Sky();
    this.envSky.material = sky.material;
    this.envSky.scale.setScalar(100);
    this.envScene.add(this.envSky);
    this.envTimer = 999;
    this.envRT = null;

    this.sunDir = new THREE.Vector3();
    this.moonDir = new THREE.Vector3();
    this.fogColor = new THREE.Color();
    this.day = 1;
    this.night = 0;
    this.dusk = 0;
    this.update(0, new THREE.Vector3());
  }

  get hours() { return (this.time * 24 + 24) % 24; }

  update(dt, focus, camera) {
    if (!this.paused) this.time = (this.time + dt / this.dayLength) % 1;
    const a = (this.time - 0.25) * Math.PI * 2;
    this.sunDir.set(Math.cos(a) * 0.82, Math.sin(a), 0.42 + Math.cos(a) * 0.1).normalize();
    this.moonDir.copy(this.sunDir).multiplyScalar(-1);
    this.moonDir.y = Math.abs(this.moonDir.y) * 0.9 + 0.12;
    this.moonDir.normalize();

    const sy = this.sunDir.y;
    this.day = smooth(-0.06, 0.2, sy);
    this.night = 1 - smooth(-0.18, 0.02, sy);
    this.dusk = (1 - smooth(0.05, 0.38, sy)) * smooth(-0.16, 0.02, sy);

    const u = this.sky.material.uniforms;
    u.sunPosition.value.copy(this.sunDir).multiplyScalar(1000);
    u.uNight.value = this.night;
    u.uMoonDir.value.copy(this.moonDir);
    u.uTime.value += dt;
    u.time.value += dt;
    u.uSkyGain.value = 0.9;

    // 霧の色
    this.fogColor.copy(lerpC(lerpC(FOG_NIGHT, FOG_DAY, this.day), FOG_DUSK, this.dusk * 0.75));
    this.scene.fog.color.copy(this.fogColor);
    this.scene.fog.density = 0.0019 + this.night * 0.0012 + this.dusk * 0.0004;
    u.uFogColor.value.copy(this.fogColor);

    // 太陽光 / 月光
    const isMoon = this.night > 0.5;
    const ldir = isMoon ? this.moonDir : this.sunDir;
    this.sun.color.copy(isMoon ? MOON : lerpC(SUN_DAY, SUN_DUSK, this.dusk));
    this.sun.intensity = isMoon ? 2.7 * this.night : 3.4 * this.day * (1 - this.dusk * 0.35);
    this.hemi.color.copy(lerpC(HEMI_SKY_NIGHT, HEMI_SKY_DAY, this.day)).lerp(FOG_DUSK, this.dusk * 0.3);
    this.hemi.groundColor.copy(lerpC(HEMI_GND_NIGHT, HEMI_GND_DAY, this.day));
    this.hemi.intensity = 0.5 + this.day * 0.3 + this.night * 0.55;

    // 影のカメラをプレイヤー周辺に追従（テクセル単位にスナップしてちらつき防止）
    const r = this.q.shadowRange;
    const texel = (2 * r) / this.q.shadow;
    const fx = Math.round(focus.x / texel) * texel, fz = Math.round(focus.z / texel) * texel;
    this.sun.target.position.set(fx, focus.y, fz);
    this.sun.position.set(fx + ldir.x * 200, focus.y + ldir.y * 200, fz + ldir.z * 200);
    this.sun.target.updateMatrixWorld();

    if (camera) this.sky.position.copy(camera.position);

    // 環境マップ（数秒おきに更新）
    this.envTimer += dt;
    if (this.envTimer > 4) {
      this.envTimer = 0;
      const old = this.envRT;
      this.envRT = this.pmrem.fromScene(this.envScene, 0.02, 0.1, 500);
      this.scene.environment = this.envRT.texture;
      if (old) old.dispose();
    }
    this.scene.environmentIntensity = 0.3 + this.day * 0.35 + this.night * 0.2;
    this.renderer.toneMappingExposure = 0.46 + this.night * 0.8 + this.dusk * 0.06;
  }
}
