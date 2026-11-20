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

function contour(): string {
  const T = 480;
  const st = 8;
  const tau = Math.PI * 2;
  const h = (x: number, y: number) =>
    0.5 * Math.sin(tau * (x / T + 0.3)) * Math.cos((tau * y) / T) +
    0.3 * Math.sin((tau * (2 * x + y)) / T + 1.3) +
    0.25 * Math.cos((tau * (x - 2 * y)) / T + 0.7) +
    0.12 * Math.sin((tau * 3 * y) / T + 2);
  let big = "";
  let small = "";
  for (let x = 0; x < T; x += st) {
    for (let y = 0; y < T; y += st) {
      const v = h(x, y) * 5;
      const d = Math.abs(v - Math.round(v));
      if (d < 0.13) big += `M${x} ${y}h0`;
      else if (x % 16 === 0 && y % 16 === 0) small += `M${x} ${y}h0`;
    }
  }
  return `<svg ${NS} width="${T}" height="${T}"><g fill="none" stroke="#000" stroke-linecap="round"><path d="${big}" stroke-width="2.6"/><path d="${small}" stroke-width="1.4" opacity=".55"/></g></svg>`;
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
