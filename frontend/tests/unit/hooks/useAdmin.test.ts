/**
 * @file tests/unit/hooks/useAdmin.test.ts
 * @brief Asserts useAdmin mutations pass resolvable toast keys.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import en from "@/i18n/en-US.json";

const spy = vi.fn((opts: unknown) => opts);
vi.mock("@/hooks/useMutationWithToast", () => ({
  useMutationWithToast: (opts: unknown) => spy(opts),
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => ({}),
}));

import * as mod from "@/hooks/useAdmin";

const last = () => spy.mock.results.at(-1)!.value as Record<string, unknown>;
const resolve = (k: string) =>
  k.split(".").reduce<unknown>((o, p) => (o as never)?.[p], en);

const CASES: [string, (() => unknown) | undefined, boolean][] = [
  ["useChangeUserRole", undefined, false],
  ["useSuspendUser", undefined, false],
  ["useRestoreUser", undefined, false],
  ["useDeleteUser", undefined, false],
  ["useUpdateAdminSettings", undefined, false],
];

describe("useAdmin toast wiring", () => {
  beforeEach(() => spy.mockClear());
  it.each(CASES)("%s has a resolvable successKey", (name, _f, silent) => {
    const fn = (mod as Record<string, (...a: never[]) => unknown>)[name];
    renderHook(() => fn("x" as never));
    const key = last().successKey as string;
    expect(typeof resolve(key)).toBe("string");
    if (silent) expect(last().silentSuccess).toBe(true);
  });
});
