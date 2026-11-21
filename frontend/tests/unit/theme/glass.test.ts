import { readFileSync } from "node:fs";
import { join } from "node:path";

const css = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");

test.each([
  ".glass",
  "backdrop-filter",
  "prefers-reduced-transparency",
  '[data-transparency="reduced"]',
  ".glass-btn",
  ".glass-lift",
])("globals.css contains %s", (needle) => {
  expect(css).toContain(needle);
});
