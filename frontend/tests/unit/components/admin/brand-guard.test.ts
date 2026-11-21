/**
 * @file tests/unit/components/admin/brand-guard.test.ts
 * @brief Static guard: admin and moderation sources use brand tokens only
 *        (no raw hex, palette colours, font-black, border-l-4 or hairlines).
 */
import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = join(__dirname, "..", "..", "..", "..");

/** @brief Recursively list .tsx/.ts files under a directory. */
function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return walk(p);
    return /\.tsx?$/.test(name) ? [p] : [];
  });
}

const FILES = [
  ...walk(join(ROOT, "components", "admin")),
  ...walk(join(ROOT, "components", "moderation")),
  ...walk(join(ROOT, "app", "app", "admin")),
  join(ROOT, "lib", "retention-policies.ts"),
];

/** Hex literals allowed: functional values, not styling. */
const HEX_ALLOW = new Set([
  "components/admin/ColorPicker.tsx", // native color input needs a hex value
]);

const RULES: { name: string; re: RegExp; allow?: Set<string> }[] = [
  {
    name: "raw hex colour",
    re: /#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/,
    allow: HEX_ALLOW,
  },
  {
    name: "Tailwind palette colour",
    re: /\b(?:text|bg|border|ring|fill|stroke)-(?:amber|red|green|purple|orange|gray|slate|zinc|neutral|blue|emerald|rose|lime|yellow|sky|indigo|violet)-\d{2,3}\b/,
  },
  { name: "font-black", re: /\bfont-black\b/ },
  { name: "left rail border", re: /\bborder-l-4\b/ },
  {
    name: "hairline row divider",
    re: /\bborder-[tb]\b[^"`]*border-ink\/(5|10|20)|max-md:border max-md:border-ink/,
  },
];

describe("admin brand guard", () => {
  for (const rule of RULES) {
    it(`has no ${rule.name}`, () => {
      const offenders: string[] = [];
      for (const file of FILES) {
        const rel = relative(ROOT, file);
        if (rule.allow?.has(rel)) continue;
        const lines = readFileSync(file, "utf8").split("\n");
        lines.forEach((line, i) => {
          if (rule.re.test(line)) offenders.push(`${rel}:${i + 1}`);
        });
      }
      expect(offenders).toEqual([]);
    });
  }
});
