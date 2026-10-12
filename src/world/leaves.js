import * as THREE from 'three';

/** 葉っぱのかたまり（アルファ付き）をキャンバスで描いたテクスチャ */
export function leafTexture(kind = 'broad') {
  const S = 256;
  const c = document.createElement('canvas');
  c.width = c.height = S;
  const g = c.getContext('2d');
  let seed = kind === 'broad' ? 7 : 13;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  g.clearRect(0, 0, S, S);
  if (kind === 'broad') {
    for (let i = 0; i < 26; i++) {
      const a = rnd() * Math.PI * 2;
      const r = 20 + rnd() * 78;
      const x = S / 2 + Math.cos(a) * r * 0.9, y = S / 2 + Math.sin(a) * r * 0.9;
      const len = 46 + rnd() * 26, wid = len * (0.42 + rnd() * 0.12);
      const rot = a + (rnd() - 0.5) * 1.2;
      g.save();
      g.translate(x, y);
      g.rotate(rot);
      const shade = 170 + rnd() * 85;
      const grd = g.createLinearGradient(-len / 2, 0, len / 2, 0);
      grd.addColorStop(0, `rgb(${shade * 0.72},${shade * 0.86},${shade * 0.6})`);
      grd.addColorStop(1, `rgb(${Math.min(255, shade * 1.05)},${Math.min(255, shade * 1.08)},${shade * 0.78})`);
      g.fillStyle = grd;
      g.beginPath();
      g.moveTo(-len / 2, 0);
      g.bezierCurveTo(-len / 4, -wid / 2, len / 4, -wid / 2, len / 2, 0);
      g.bezierCurveTo(len / 4, wid / 2, -len / 4, wid / 2, -len / 2, 0);
      g.fill();
      g.strokeStyle = `rgba(60,80,40,0.45)`;
      g.lineWidth = 1.6;
      g.beginPath(); g.moveTo(-len / 2, 0); g.lineTo(len / 2.2, 0); g.stroke();
      g.lineWidth = 0.8;
      for (let k = -2; k <= 2; k++) {
        if (!k) continue;
        g.beginPath(); g.moveTo(k * len / 7, 0); g.lineTo(k * len / 7 + len / 9, (k > 0 ? 1 : -1) * wid / 2.8); g.stroke();
      }
      g.restore();
    }
  } else {
    // 針葉樹：放射状の細い葉
    for (let b = 0; b < 7; b++) {
      const a0 = rnd() * Math.PI * 2;
      const bx = S / 2 + Math.cos(a0) * 30, by = S / 2 + Math.sin(a0) * 30;
      for (let i = 0; i < 40; i++) {
        const a = a0 + (rnd() - 0.5) * 1.6;
        const len = 40 + rnd() * 50;
        const shade = 150 + rnd() * 105;
        g.strokeStyle = `rgb(${shade * 0.75},${shade * 0.9},${shade * 0.7})`;
        g.lineWidth = 2 + rnd() * 1.5;
        g.lineCap = 'round';
        g.beginPath();
        g.moveTo(bx, by);
        g.lineTo(bx + Math.cos(a) * len, by + Math.sin(a) * len);
        g.stroke();
      }
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  return t;
}
