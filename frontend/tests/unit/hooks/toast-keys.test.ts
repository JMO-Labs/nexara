/**
 * @file tests/unit/hooks/toast-keys.test.ts
 * @brief Every toast key referenced by hooks must exist in en-US.json.
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import en from "@/i18n/en-US.json";

const dir = path.resolve(__dirname, "../../../hooks");
const resolve = (k: string) =>
  k.split(".").reduce<unknown>((o, p) => (o as never)?.[p], en);

describe("hook toast keys", () => {
  it("all successKey/errorKey values resolve", () => {
    const missing: string[] = [];
    for (const f of fs.readdirSync(dir).filter((x) => x.endsWith(".ts"))) {
      const src = fs.readFileSync(path.join(dir, f), "utf8");
      for (const m of src.matchAll(/(?:successKey|errorKey): "([^"]+)"/g)) {
        if (typeof resolve(m[1]) !== "string") missing.push(`${f}:${m[1]}`);
      }
    }
    expect(missing).toEqual([]);
  });
  it("auth failure keys exist", () => {
    for (const k of [
      "toasts.auth.login.failed",
      "toasts.auth.register.failed",
      "toasts.auth.magicLink.failed",
      "toasts.auth.magicLink.sent",
      "toasts.auth.reset.sent",
      "toasts.auth.reset.failed",
      "toasts.auth.reset.done",
    ])
      expect(typeof resolve(k)).toBe("string");
  });
});
