import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { FXAAPass } from 'three/addons/postprocessing/FXAAPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';

/** 環境遮蔽（AO）の計算に含めないもの（草・葉のカード・海など、形がシェーダーで決まるもの） */
export const NO_AO = new Set();

export const QUALITY = {
  ultra: { label: '最高', pixelRatio: 2, shadow: 4096, shadowRange: 70, msaa: 4, bloom: true, ao: true, grass: 90000, grassRadius: 56, flowers: 6000, lodNear: 150, far: 1100 },
  high: { label: '高', pixelRatio: 1.5, shadow: 2048, shadowRange: 55, msaa: 4, bloom: true, grass: 45000, grassRadius: 42, flowers: 3000, lodNear: 110, far: 850 },
  low: { label: '軽量', pixelRatio: 1, shadow: 1024, shadowRange: 40, msaa: 0, bloom: false, grass: 14000, grassRadius: 28, flowers: 1000, lodNear: 70, far: 600 },
};

export function loadQualityKey() {
  // スマホ・タブレットは「高」、PC は「最高」から始める（設定で変更可）
  const mobile = matchMedia('(pointer: coarse)').matches || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  const def = mobile ? 'high' : 'ultra';
  try { return localStorage.getItem('hikari_quality') || def; } catch { return def; }
}
export function saveQualityKey(k) {
  try { localStorage.setItem('hikari_quality', k); } catch { /* noop */ }
}

// 色調補正 + ビネット + フィルムグレイン（トーンマッピング前のリニア空間で処理）
const GradeShader = {
  uniforms: {
    tDiffuse: { value: null },
    uTime: { value: 0 },
    uSaturation: { value: 1.14 },
    uContrast: { value: 1.04 },
    uTint: { value: new THREE.Vector3(1, 1, 1) },
    uVignette: { value: 0.32 },
    uDesat: { value: 0 },
    uBlur: { value: 0 },
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
  `,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    uniform float uTime, uSaturation, uContrast, uVignette, uDesat, uBlur;
    uniform vec3 uTint;
    varying vec2 vUv;
    float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main() {
      vec4 c = texture2D(tDiffuse, vUv);
      if (uBlur > 0.0) {
        vec2 d = (vUv - 0.5) * uBlur * 0.04;
        c.rgb = (c.rgb + texture2D(tDiffuse, vUv - d).rgb + texture2D(tDiffuse, vUv - d * 2.0).rgb + texture2D(tDiffuse, vUv - d * 3.0).rgb) * 0.25;
      }
      vec3 col = c.rgb * uTint;
      float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
      col = mix(vec3(l), col, uSaturation * (1.0 - uDesat));
      col = (col - 0.18) * uContrast + 0.18;
      col = max(col, 0.0);
      vec2 q = vUv - 0.5;
      float v = 1.0 - dot(q, q) * uVignette * 2.2;
      col *= clamp(v, 0.0, 1.0);
      col += (hash(vUv * 1000.0 + uTime) - 0.5) * 0.008;
      gl_FragColor = vec4(col, c.a);
    }
  `,
};

export class Renderer {
  constructor(canvas, q) {
    this.q = q;
    const r = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance', stencil: false });
    r.setPixelRatio(Math.min(window.devicePixelRatio || 1, q.pixelRatio));
    r.setSize(window.innerWidth, window.innerHeight, false);
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFShadowMap;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.0;
    r.outputColorSpace = THREE.SRGBColorSpace;
    this.r = r;

    const size = r.getDrawingBufferSize(new THREE.Vector2());
    const rt = new THREE.WebGLRenderTarget(size.x, size.y, {
      type: THREE.HalfFloatType,
      samples: q.msaa,
    });
    this.composer = new EffectComposer(r, rt);
    this.renderPass = new RenderPass(null, null);
    this.composer.addPass(this.renderPass);
    if (q.bloom) {
      this.bloom = new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), 0.38, 0.45, 3.2);
      this.composer.addPass(this.bloom);
    }
    this.grade = new ShaderPass(GradeShader);
    this.composer.addPass(this.grade);
    this.composer.addPass(new OutputPass());
    if (!q.msaa) {
      this.fxaa = new FXAAPass();
      this.composer.addPass(this.fxaa);
    }
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.r.setSize(w, h, false);
    this.composer.setSize(w, h);
    this.composer.setPixelRatio(this.r.getPixelRatio());
    if (this.onResize) this.onResize(w, h);
  }

  /** 物の接するところ・すみの陰（GTAO）。最高画質のみ */
  setupAO(scene, camera) {
    const size = this.r.getDrawingBufferSize(new THREE.Vector2());
    const p = new GTAOPass(scene, camera, size.x, size.y);
    p.output = GTAOPass.OUTPUT.Default;
    p.blendIntensity = 0.85;
    p.updateGtaoMaterial({ radius: 0.9, distanceExponent: 1.6, thickness: 1.2, scale: 1.0, samples: 16, distanceFallOff: 1.0 });
    p.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 16 });
    const hidden = [];
    const ov = p._overrideVisibility.bind(p), rv = p._restoreVisibility.bind(p);
    p._overrideVisibility = () => {
      ov();
      for (const o of NO_AO) if (o.visible) { o.visible = false; hidden.push(o); }
    };
    p._restoreVisibility = () => {
      for (const o of hidden) o.visible = true;
      hidden.length = 0;
      rv();
    };
    this.composer.insertPass(p, 1);
    this.gtao = p;
  }

  render(scene, camera, t) {
    if (this.q.ao && !this.gtao) this.setupAO(scene, camera);
    if (this.gtao) { this.gtao.scene = scene; this.gtao.camera = camera; }
    this.renderPass.scene = scene;
    this.renderPass.camera = camera;
    this.grade.uniforms.uTime.value = t;
    this.composer.render();
  }
}
