/**
 * @file patterns.ts
 * @brief Home background pattern names and their SVG mask generators.
 */

/** @brief Pattern names accepted by settings and branding (must match backend regex). */
export const PATTERNS = [
  "none",
  "dots",
  "topo",
  "contour",
  "waves",
  "grain",
] as const;

/** @brief One of {@link PATTERNS}. */
export type HomePattern = (typeof PATTERNS)[number];

const enc = (s: string) => `url("data:image/svg+xml,${encodeURIComponent(s)}")`;
const NS = 'xmlns="http://www.w3.org/2000/svg"';

function topo(): string {
  let d = "";
  for (const [cx, cy] of [
    [110, 120],
    [330, 300],
  ]) {
    for (let r = 18; r < 170; r += 16) {
      let p = "";
      for (let a = 0; a <= 64; a++) {
        const t = (a / 64) * Math.PI * 2;
        const rr =
          r * (1 + 0.12 * Math.sin(3 * t + r / 30) + 0.06 * Math.cos(5 * t));
        p += `${a ? "L" : "M"}${(cx + rr * Math.cos(t)).toFixed(1)} ${(cy + rr * 0.8 * Math.sin(t)).toFixed(1)}`;
      }
      d += p + "Z";
    }
  }
  return `<svg ${NS} width="440" height="440"><path d="${d}" fill="none" stroke="#000" stroke-width="1"/></svg>`;
}

/**
 * @brief Topographic contour lines: marching squares over a tileable
 *        height field (integer frequencies over T so edges wrap).
 */
function contour(): string {
  const T = 640;
  const st = 8;
  const n = T / st;
  const k = (Math.PI * 2) / T;
  const h = (x: number, y: number) =>
    Math.sin(k * x + 0.3) * Math.cos(k * y) +
    0.6 * Math.sin(k * (2 * x + y) + 1.3) +
    0.45 * Math.cos(k * (x - 2 * y) + 0.7) +
    0.25 * Math.sin(k * 3 * y + 2) +
    0.15 * Math.cos(k * (3 * x + 2 * y) + 0.4);
  const g: number[][] = [];
  for (let i = 0; i <= n; i++) {
    g.push([]);
    for (let j = 0; j <= n; j++) g[i].push(h(i * st, j * st));
  }
  const f = (v: number) => +v.toFixed(1);
  let d = "";
  for (let L = -2.2; L <= 2.2; L += 0.22) {
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        const x = i * st;
        const y = j * st;
        // corners: tl, tr, br, bl
        const c = [g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]];
        const xy = [
          [x, y],
          [x + st, y],
          [x + st, y + st],
          [x, y + st],
        ];
        const pts: string[] = [];
        for (let e = 0; e < 4; e++) {
          const a = c[e];
          const b = c[(e + 1) % 4];
          if (a < L !== b < L) {
            const t = (L - a) / (b - a);
            const [x0, y0] = xy[e];
            const [x1, y1] = xy[(e + 1) % 4];
            pts.push(`${f(x0 + t * (x1 - x0))} ${f(y0 + t * (y1 - y0))}`);
          }
        }
        // ponytail: saddle cells (4 crossings) pair in edge order; fine at this scale
        for (let q = 0; q + 1 < pts.length; q += 2)
          d += `M${pts[q]}L${pts[q + 1]}`;
      }
    }
  }
  return `<svg ${NS} width="${T}" height="${T}"><path d="${d}" fill="none" stroke="#000" stroke-width="1" stroke-linecap="round"/></svg>`;
}

const SVGS: Record<Exclude<HomePattern, "none">, () => string> = {
  contour,
  topo,
  dots: () =>
    `<svg ${NS} width="20" height="20"><circle cx="2" cy="2" r="1.2"/></svg>`,
  waves: () =>
    `<svg ${NS} width="120" height="28"><path d="M0 14 Q30 2 60 14 T120 14" fill="none" stroke="#000" stroke-width="1.1"/></svg>`,
  grain: () =>
    `<svg ${NS} width="180" height="180"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1.6 -.55"/></filter><rect width="180" height="180" filter="url(#n)"/></svg>`,
};

/**
 * @brief CSS `url()` of an SVG mask for a pattern.
 * @param p pattern name
 * @return css url string, or null for "none"
 */
export function patternUrl(p: HomePattern): string | null {
  return p === "none" ? null : enc(SVGS[p]());
}
