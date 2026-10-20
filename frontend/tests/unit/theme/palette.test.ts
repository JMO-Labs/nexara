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

test("forest text on lilac fill meets AA", () => {
  expect(
    contrastRatio(palette.light["surface-strong"], palette.light.accent),
  ).toBeGreaterThanOrEqual(4.5);
});
