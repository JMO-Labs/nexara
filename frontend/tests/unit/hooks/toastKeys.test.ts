/**
 * @file tests/unit/hooks/toastKeys.test.ts
 * @brief useEvents / useSettings / useAdmin pass the expected toast keys.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";

const spy = vi.fn((opts: unknown) => opts);
vi.mock("@/hooks/useMutationWithToast", () => ({
  useMutationWithToast: (opts: unknown) => spy(opts),
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => ({}),
}));

import {
  useCreateEvent,
  useUpdateEvent,
  useDeleteEvent,
} from "@/hooks/useEvents";
import * as settings from "@/hooks/useSettings";
import * as admin from "@/hooks/useAdmin";

const last = () => spy.mock.results.at(-1)!.value as Record<string, unknown>;

describe("toast keys", () => {
  beforeEach(() => spy.mockClear());

  it("events", () => {
    renderHook(() => useCreateEvent());
    expect(last().successKey).toBe("toasts.events.created");
    renderHook(() => useUpdateEvent("e1"));
    expect(last().successKey).toBe("toasts.events.updated");
    renderHook(() => useDeleteEvent());
    expect(last().successKey).toBe("toasts.events.cancelled");
  });

  it("settings: every mutation has a settings key", () => {
    const hooks = Object.entries(settings).filter(([n]) =>
      /^use(Update|Change|Save)/.test(n),
    );
    expect(hooks.length).toBeGreaterThan(0);
    for (const [, h] of hooks) {
      spy.mockClear();
      renderHook(() => (h as () => unknown)());
      expect(String(last().successKey)).toMatch(/^toasts\.settings\./);
    }
  });

  it("admin: restore, delete, settings have keys", () => {
    for (const h of [
      admin.useRestoreUser,
      admin.useDeleteUser,
      admin.useUpdateAdminSettings,
    ]) {
      spy.mockClear();
      renderHook(() => h());
      expect(String(last().successKey)).toMatch(/^toasts\.admin\./);
    }
  });
});
