import { palette } from "@/theme/palette";
import { contrastRatio } from "@/lib/contrast";

test("contrastRatio known pair", () => {
  expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 0);
});

test.each(["light", "dark"] as const)("%s palette meets AA", (mode) => {
  const p = palette[mode];
  expect(contrastRatio(p.ink, p.bg)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.ink, p.surface)).toBeGreaterThanOrEqual(4.5);
  // surface-strong is now an inverted fill; page bg is its readable foreground
  expect(contrastRatio(p.bg, p["surface-strong"])).toBeGreaterThanOrEqual(4.5);
  // secondary text sits on page/cards; nav-muted sits on the glass nav pill
  expect(contrastRatio(p.muted, p.bg)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.muted, p.surface)).toBeGreaterThanOrEqual(4.5);
  expect(
    contrastRatio(p["nav-muted"], p["glass-solid"]),
  ).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.danger, p.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.danger, p.bg)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.ink, p["glass-solid"])).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.muted, p["glass-solid"])).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.accent, p.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p["danger-fg"], p.danger)).toBeGreaterThanOrEqual(4.5);
});

test("glass bento palette values", () => {
  expect(palette.light.bg).toBe("#E4E4E4");
  expect(palette.dark.bg).toBe("#0D1117");
  expect(palette.light.blue).toBe("#83A2DB");
  expect(palette.dark.ok).toBe("#5CC08A");
});

test.each(["light", "dark"] as const)(
  "%s destructive bg vs foreground meets AA",
  (mode) => {
    const p = palette[mode];
    expect(contrastRatio(p["danger-fg"], p.danger)).toBeGreaterThanOrEqual(4.5);
  },
);

test.each(["light", "dark"] as const)(
  "%s page-bg text on accent fill meets AA",
  (mode) => {
    const p = palette[mode];
    expect(contrastRatio(p.bg, p.accent)).toBeGreaterThanOrEqual(4.5);
  },
);

/** Blend fg over bg at the given alpha (EmptyState uses opacity-80 text). */
function blend(fg: string, bg: string, a: number): string {
  const ch = (h: string, i: number) =>
    parseInt(h.slice(1 + i * 2, 3 + i * 2), 16);
  const m = [0, 1, 2].map((i) =>
    Math.round(ch(fg, i) * a + ch(bg, i) * (1 - a))
      .toString(16)
      .padStart(2, "0"),
  );
  return `#${m.join("")}`;
}

test.each(["light", "dark"] as const)("%s feed text pairs meet AA", (mode) => {
  const p = palette[mode];
  // PostCard body (ink) and meta (muted) on the card surface
  expect(contrastRatio(p.ink, p.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.muted, p.surface)).toBeGreaterThanOrEqual(4.5);
  // EmptyState description: text-ink opacity-80 on page bg
  expect(contrastRatio(blend(p.ink, p.bg, 0.8), p.bg)).toBeGreaterThanOrEqual(
    4.5,
  );
});
