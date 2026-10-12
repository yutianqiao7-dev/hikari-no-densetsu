/** 当たり判定（回転した箱と円）。空間ハッシュで近傍だけ調べる */
export class Colliders {
  constructor() { this.cell = 16; this.map = new Map(); }
  key(i, j) { return i * 73856093 ^ j * 19349663; }
  add(c) {
    const r = c.r ?? Math.hypot(c.hw, c.hd);
    const i0 = Math.floor((c.x - r) / this.cell), i1 = Math.floor((c.x + r) / this.cell);
    const j0 = Math.floor((c.z - r) / this.cell), j1 = Math.floor((c.z + r) / this.cell);
    for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) {
      const k = this.key(i, j);
      if (!this.map.has(k)) this.map.set(k, []);
      this.map.get(k).push(c);
    }
  }
  near(x, z) { return this.map.get(this.key(Math.floor(x / this.cell), Math.floor(z / this.cell))) || []; }
  /** 半径 rad の円を押し出す。押し出したら true */
  resolve(p, rad) {
    let hit = false;
    for (const c of this.near(p.x, p.z)) {
      if (c.disabled) continue;
      if (c.r != null) {
        const dx = p.x - c.x, dz = p.z - c.z, d = Math.hypot(dx, dz), m = c.r + rad;
        if (d < m && d > 1e-5) { p.x = c.x + (dx / d) * m; p.z = c.z + (dz / d) * m; hit = true; }
        continue;
      }
      const cs = Math.cos(c.rot), sn = Math.sin(c.rot);
      const dx = p.x - c.x, dz = p.z - c.z;
      const lx = dx * cs - dz * sn, lz = dx * sn + dz * cs;
      const qx = Math.max(-c.hw, Math.min(c.hw, lx)), qz = Math.max(-c.hd, Math.min(c.hd, lz));
      let ex = lx - qx, ez = lz - qz;
      let d = Math.hypot(ex, ez);
      if (d >= rad) continue;
      let nlx, nlz;
      if (d < 1e-5) {
        // 中に入り込んだ：一番近い面へ
        const px = c.hw - Math.abs(lx), pz = c.hd - Math.abs(lz);
        if (px < pz) { nlx = Math.sign(lx) * (c.hw + rad); nlz = lz; } else { nlx = lx; nlz = Math.sign(lz) * (c.hd + rad); }
      } else {
        nlx = qx + (ex / d) * rad; nlz = qz + (ez / d) * rad;
      }
      p.x = c.x + nlx * cs + nlz * sn;
      p.z = c.z - nlx * sn + nlz * cs;
      hit = true;
    }
    return hit;
  }
}
