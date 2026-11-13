/**
 * @file tests/unit/hooks/mutationToastCoverage.test.ts
 * @brief Every mutation in the Phase 2 hooks declares a successKey (or is
 *        silent) and every referenced i18n key exists in en-US.
 */
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import en from "@/i18n/en-US.json";

const HOOKS = [
  "useChat",
  "useEvents",
  "useGalleries",
  "useMedia",
  "useSubgroups",
  "useSettings",
  "useInvites",
  "useAdmin",
  "useAdminOauth",
  "usePushNotifications",
  "useCalendarSubscriptions",
];

const src = (n: string) =>
  readFileSync(resolve(__dirname, `../../../hooks/${n}.ts`), "utf8");

const lookup = (key: string): unknown =>
  key.split(".").reduce<unknown>((o, k) => (o as never)?.[k], en);

describe.each(HOOKS)("%s toast wiring", (name) => {
  const code = src(name);
  const blocks = code.split(/useMutationWithToast[<(]/).slice(1);

  it("does not use raw useMutation", () => {
    expect(code).not.toMatch(/\buseMutation\(/);
  });

  it.each(blocks.map((b, i) => [i, b]))(
    "mutation #%i has successKey",
    (_i, b) => {
      const block = String(b).split(/\nexport |\nfunction /)[0];
      expect(block).toMatch(/successKey:|silentSuccess:\s*true/);
    },
  );

  it("all referenced keys exist in en-US", () => {
    const keys = [...code.matchAll(/(?:successKey|errorKey):\s*"([^"]+)"/g)];
    for (const [, k] of keys) expect(lookup(k), k).toBeTypeOf("string");
  });
});

describe("auth pages", () => {
  it.each(["login", "register", "magic-link", "reset-password"])(
    "%s uses useMutationWithToast",
    (p) => {
      const code = readFileSync(
        resolve(__dirname, `../../../app/(auth)/${p}/page.tsx`),
        "utf8",
      );
      expect(code).toContain("useMutationWithToast");
      expect(code).not.toContain("setError(");
    },
  );
  it("auth toast keys exist", () => {
    for (const k of [
      "toasts.auth.login.failed",
      "toasts.auth.register.failed",
      "toasts.auth.magicLink.failed",
      "toasts.auth.reset.sent",
      "toasts.auth.reset.failed",
      "toasts.auth.reset.confirmFailed",
    ])
      expect(lookup(k), k).toBeTypeOf("string");
  });
});
