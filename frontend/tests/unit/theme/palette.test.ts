import { palette } from "@/theme/palette";
import { contrastRatio } from "@/lib/contrast";

test("contrastRatio known pair", () => {
  expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 0);
});

test.each(["light", "dark"] as const)("%s palette meets AA", (mode) => {
  const p = palette[mode];
  expect(contrastRatio(p.ink, p.bg)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.ink, p.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.accent, p["surface-strong"])).toBeGreaterThanOrEqual(
    4.5,
  );
  // secondary text sits on page/cards; nav-muted sits on the forest nav bars
  expect(contrastRatio(p.muted, p.bg)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.muted, p.surface)).toBeGreaterThanOrEqual(4.5);
  expect(
    contrastRatio(p["nav-muted"], p["surface-strong"]),
  ).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.danger, p.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.danger, p.bg)).toBeGreaterThanOrEqual(4.5);
});

test.each(["light", "dark"] as const)(
  "%s destructive bg vs foreground meets AA",
  (mode) => {
    const p = palette[mode];
    expect(contrastRatio(p["danger-fg"], p.danger)).toBeGreaterThanOrEqual(4.5);
  },
);

test("forest text on lilac fill meets AA", () => {
  expect(
    contrastRatio(palette.light["surface-strong"], palette.light.accent),
  ).toBeGreaterThanOrEqual(4.5);
});

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
