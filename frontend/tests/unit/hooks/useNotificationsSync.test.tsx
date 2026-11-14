/**
 * @file tests/unit/hooks/useNotificationsSync.test.tsx
 * @brief Sync hook: per-event invalidation and auth gating.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const sse = vi.hoisted(() => ({
  opts: null as null | Record<string, unknown>,
}));
vi.mock("@/lib/api/notifications", () => ({ STREAM_PATH: "/s" }));
vi.mock("@/hooks/useSSE", () => ({
  useSSE: (_p: string, o: Record<string, unknown>) => {
    sse.opts = o;
  },
}));
const session = vi.hoisted(() => ({ status: "authenticated" }));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: { status: string }) => unknown) => sel(session),
}));

import { useNotificationsSync } from "@/hooks/useNotificationsSync";

function run(types?: readonly string[]) {
  const qc = new QueryClient();
  const spy = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  renderHook(() => useNotificationsSync(types), { wrapper });
  return spy;
}
const emit = (t: string) =>
  (sse.opts?.onMessage as (d: unknown, t: string) => void)({}, t);

describe("useNotificationsSync", () => {
  beforeEach(() => {
    session.status = "authenticated";
  });

  it("dismissed invalidates ['notifications']", () => {
    const spy = run();
    emit("user_notification_dismissed");
    expect(spy).toHaveBeenCalledWith({ queryKey: ["notifications"] });
  });

  it("prefs updated invalidates preferences only", () => {
    const spy = run();
    emit("user_preferences_updated");
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith({
      queryKey: ["notifications", "preferences"],
    });
  });

  it("is disabled when unauthenticated", () => {
    session.status = "anonymous";
    run();
    expect(sse.opts?.enabled).toBe(false);
  });

  it("subscribes only to the given event types", () => {
    run(["user_preferences_updated"]);
    expect(sse.opts?.eventTypes).toEqual(["user_preferences_updated"]);
  });
});
