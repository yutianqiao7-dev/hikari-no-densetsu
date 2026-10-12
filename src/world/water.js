import * as THREE from 'three';
import { NOISE } from './glsl.js';

/** 海と湖。地形の高さテクスチャから水深を求め、浅瀬の色・波打ち際の泡・空の反射・太陽のきらめきを描く */
export function createWater(hf, heightTex, sky) {
  const uniforms = THREE.UniformsUtils.merge([
    THREE.UniformsLib.fog,
    {
      uTime: { value: 0 },
      uHeight: { value: null },
      uHF: { value: new THREE.Vector4() },
      uSunDir: { value: new THREE.Vector3(0, 1, 0) },
      uSunColor: { value: new THREE.Color(1, 1, 1) },
      uSunI: { value: 1 },
      uZenith: { value: new THREE.Color(0.2, 0.4, 0.8) },
      uHorizon: { value: new THREE.Color(0.6, 0.7, 0.9) },
      uDay: { value: 1 },
    },
  ]);
  uniforms.uHeight.value = heightTex;
  uniforms.uHF.value.copy(hf.uvParams);

  const mat = new THREE.ShaderMaterial({
    uniforms,
    fog: true,
    transparent: true,
    depthWrite: false,
    vertexShader: /* glsl */`
      #include <common>
      #include <fog_pars_vertex>
      varying vec3 vW;
      void main() {
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vW = wp.xyz;
        vec4 mvPosition = viewMatrix * wp;
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }
    `,
    fragmentShader: /* glsl */`
      #include <common>
      #include <fog_pars_fragment>
      uniform float uTime, uSunI, uDay;
      uniform sampler2D uHeight;
      uniform vec4 uHF;
      uniform vec3 uSunDir, uSunColor, uZenith, uHorizon;
      varying vec3 vW;
      ${NOISE}
      float terrainH(vec2 p) {
        vec2 g = (p + uHF.x) / uHF.y;
        if (g.x < 0.0 || g.y < 0.0 || g.x > uHF.z - 1.0 || g.y > uHF.z - 1.0) return -14.0;
        return texture2D(uHeight, (g + 0.5) / uHF.z).r;
      }
      vec2 ngrad(vec2 q) {
        float e = 0.12;
        float n0 = vnoise(q);
        return vec2(vnoise(q + vec2(e, 0.0)) - n0, vnoise(q + vec2(0.0, e)) - n0) / e;
      }
      vec2 waveGrad(vec2 p, float t) {
        vec2 g = vec2(0.0);
        // ゆったりしたうねり（2 方向）
        g += vec2(0.8, 0.35) * cos(dot(p, vec2(0.8, 0.35)) * 0.09 + t * 0.55) * 0.05;
        g += vec2(-0.3, 0.9) * cos(dot(p, vec2(-0.3, 0.9)) * 0.13 + t * 0.7) * 0.035;
        // 方向の違うノイズを重ねて自然な波面に
        g += ngrad(p * 0.18 + vec2(t * 0.05, t * 0.03)) * 0.22;
        g += ngrad(vec2(p.y, -p.x) * 0.41 + vec2(-t * 0.08, t * 0.06)) * 0.12;
        g += ngrad(p * 1.1 + vec2(t * 0.22, -t * 0.15)) * 0.06;
        g += ngrad(vec2(-p.y, p.x) * 2.6 + vec2(t * 0.35, t * 0.28)) * 0.025;
        return g;
      }
      void main() {
        vec2 p = vW.xz;
        float th = terrainH(p);
        float depth = max(0.0, vW.y - th);
        vec3 V = normalize(cameraPosition - vW);
        float dist = length(cameraPosition - vW);
        vec2 g = waveGrad(p, uTime) * mix(1.0, 0.2, smoothstep(40.0, 420.0, dist));
        vec3 n = normalize(vec3(-g.x, 1.0, -g.y));
        float ndv = max(dot(n, V), 0.0);
        float fres = 0.02 + 0.98 * pow(1.0 - ndv, 5.0);
        vec3 R = reflect(-V, n);
        vec3 skyc = mix(uHorizon, uZenith, smoothstep(-0.05, 0.45, R.y));

        vec3 deep = vec3(0.01, 0.075, 0.16);
        vec3 mid = vec3(0.02, 0.2, 0.3);
        vec3 shallow = vec3(0.08, 0.5, 0.46);
        vec3 wc = mix(shallow, mid, smoothstep(0.0, 2.5, depth));
        wc = mix(wc, deep, smoothstep(2.5, 12.0, depth));
        float light = 0.18 + 0.82 * uDay;
        // 太陽の透過（波の山が明るく）
        float sss = pow(max(dot(V, -uSunDir + n * 0.6), 0.0), 3.0) * 0.25;
        wc = wc * light + vec3(0.05, 0.3, 0.25) * sss * uDay;
        vec3 col = mix(wc, skyc, fres);
        float spec = pow(max(dot(R, uSunDir), 0.0), 600.0) * 6.0 + pow(max(dot(R, uSunDir), 0.0), 60.0) * 0.25;
        col += uSunColor * spec * uSunI;

        // 波打ち際の泡
        float t = uTime;
        float shoreN = vnoise(p * 0.6 + t * 0.1);
        float bands = smoothstep(0.65, 1.0, sin(depth * 7.0 - t * 1.6 + shoreN * 4.0) * 0.5 + 0.5) * smoothstep(1.4, 0.2, depth);
        float edge = smoothstep(0.35, 0.0, depth + (shoreN - 0.5) * 0.25);
        float foam = max(bands * 0.8, edge) * (0.55 + 0.45 * vnoise(p * 6.0 - t * 0.6));
        col = mix(col, vec3(0.92, 0.96, 1.0) * light, foam * 0.85);

        float alpha = mix(0.25, 0.94, smoothstep(0.0, 3.0, depth));
        alpha = max(alpha, fres * 0.9);
        alpha = max(alpha, foam);
        alpha = mix(alpha, 1.0, smoothstep(150.0, 600.0, dist));
        gl_FragColor = vec4(col, alpha);
        #include <fog_fragment>
      }
    `,
  });

  const geo = new THREE.PlaneGeometry(3000, 3000, 1, 1);
  geo.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.name = 'Ocean';
  mesh.renderOrder = 2;
  mesh.frustumCulled = false;

  mesh.update = (dt, skySys) => {
    uniforms.uTime.value += dt;
    uniforms.uSunDir.value.copy(skySys.night > 0.5 ? skySys.moonDir : skySys.sunDir);
    uniforms.uSunColor.value.copy(skySys.sun.color);
    uniforms.uSunI.value = skySys.night > 0.5 ? 0.35 : skySys.day;
    uniforms.uDay.value = Math.max(skySys.day, 0.08);
    uniforms.uHorizon.value.copy(skySys.fogColor);
    uniforms.uZenith.value.setRGB(0.28, 0.5, 0.95).multiplyScalar(Math.max(skySys.day, 0.12)).lerp(skySys.fogColor, skySys.dusk * 0.5 + skySys.night * 0.5);
  };
  return mesh;
}
