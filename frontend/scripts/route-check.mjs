/**
 * @file scripts/route-check.mjs
 * @brief Migration gate: walks imports from route entry files and fails if any
 *        reachable file imports Joy/Emotion/Heroicons or has a tsc error.
 *        Catches runtime prop mismatches that "page compiles" checks miss.
 *
 * usage (from frontend/): node scripts/route-check.mjs app/app/page.tsx app/app/layout.tsx ...
 */
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const root = process.cwd();
const EXT = [".tsx", ".ts", ".jsx", ".js", ".mjs", "/index.tsx", "/index.ts"];
const BAD = /^(@mui\/|@emotion\/|@heroicons\/|@\/theme\/(joy-theme|tokens))/;
const IMPORT =
  /(?:from\s*|import\s*\(\s*|import\s+|require\(\s*)["']([^"']+)["']/g;

function resolve(from, spec) {
  let base;
  if (spec.startsWith("@/")) base = path.join(root, spec.slice(2));
  else if (spec.startsWith(".")) base = path.resolve(path.dirname(from), spec);
  else return null;
  for (const x of ["", ...EXT]) {
    const p = base + x;
    if (fs.existsSync(p) && fs.statSync(p).isFile()) return p;
  }
  return null;
}

const seen = new Set();
const joy = [];
function walk(f) {
  if (seen.has(f)) return;
  seen.add(f);
  for (const [, spec] of fs.readFileSync(f, "utf8").matchAll(IMPORT)) {
    if (BAD.test(spec)) joy.push(`${path.relative(root, f)} -> ${spec}`);
    const r = resolve(f, spec);
    if (r) walk(r);
  }
}
process.argv.slice(2).forEach((e) => walk(path.resolve(root, e)));

let tscOut = "";
try {
  execFileSync("npx", ["tsc", "--noEmit"], { cwd: root, stdio: "pipe" });
} catch (e) {
  tscOut = e.stdout.toString();
}
const reach = new Set([...seen].map((f) => path.relative(root, f)));
const tsc = tscOut.split("\n").filter((l) => reach.has(l.split("(")[0]));

joy.forEach((l) => console.log("JOY", l));
tsc.forEach((l) => console.log("TSC", l));
console.log(
  `visited ${seen.size} files: ${joy.length} joy imports, ${tsc.length} tsc errors`,
);
process.exit(joy.length || tsc.length ? 1 : 0);
