/**
 * @file tests/unit/pwa-query-persist.test.tsx
 * @brief Query cache persistence: restore offline, exclusions, logout purge.
 */
import "fake-indexeddb/auto";
import { describe, it, expect, afterEach } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import {
  persistQueryClientSave,
  persistQueryClientRestore,
} from "@tanstack/react-query-persist-client";
import { get } from "idb-keyval";
import {
  PERSIST_KEY,
  persistOptionsFor,
  shouldPersist,
  clearPersistedQueries,
} from "@/lib/pwa/queryPersist";
import { clearUserCache } from "@/lib/pwa/clearUserCache";

const opts = (user = "a") => persistOptionsFor(user);

afterEach(() => clearPersistedQueries());

describe("query persistence", () => {
  it("restores a persisted query after reload while offline", async () => {
    const a = new QueryClient();
    a.setQueryData(["events", "detail", "1"], { title: "Party" });
    await persistQueryClientSave({ queryClient: a, ...opts() });
    const b = new QueryClient();
    await persistQueryClientRestore({ queryClient: b, ...opts() });
    expect(b.getQueryData(["events", "detail", "1"])).toEqual({
      title: "Party",
    });
  });

  it("does not persist auth/admin/2fa keys or failed queries", async () => {
    const a = new QueryClient();
    a.setQueryData(["auth", "me"], { id: 1 });
    a.setQueryData(["admin", "x"], 1);
    a.setQueryData(["2fa", "status"], 1);
    a.setQueryData(["feed"], 1);
    await persistQueryClientSave({ queryClient: a, ...opts() });
    const b = new QueryClient();
    await persistQueryClientRestore({ queryClient: b, ...opts() });
    expect(b.getQueryData(["auth", "me"])).toBeUndefined();
    expect(b.getQueryData(["admin", "x"])).toBeUndefined();
    expect(b.getQueryData(["2fa", "status"])).toBeUndefined();
    expect(b.getQueryData(["feed"])).toBe(1);
    expect(
      shouldPersist({
        queryKey: ["feed"],
        state: { status: "error" },
      } as never),
    ).toBe(false);
  });

  it("logout purge clears the persisted store", async () => {
    const a = new QueryClient();
    a.setQueryData(["feed"], 1);
    await persistQueryClientSave({ queryClient: a, ...opts() });
    expect(await get(PERSIST_KEY)).toBeDefined();
    clearUserCache();
    await new Promise((r) => setTimeout(r, 50));
    expect(await get(PERSIST_KEY)).toBeUndefined();
  });

  it.each([
    ["notifications", "apprise"],
    ["notifications", "webhooks"],
    ["notifications", "preferences"],
    ["events", "subscriptions"],
    ["users", "sso"],
  ])("denies %s/%s but not siblings", (h, sec) => {
    const st = { status: "success" };
    expect(shouldPersist({ queryKey: [h, sec], state: st } as never)).toBe(
      false,
    );
    expect(shouldPersist({ queryKey: [h, "list"], state: st } as never)).toBe(
      true,
    );
  });

  it("never persists paused/offline mutations", async () => {
    const a = new QueryClient();
    a.getMutationCache().build(a, {
      mutationFn: async () => 1,
      mutationKey: ["pw"],
    });
    const m = a.getMutationCache().getAll()[0];
    m.state = {
      ...m.state,
      isPaused: true,
      variables: { password: "hunter2" },
    } as never;
    await persistQueryClientSave({ queryClient: a, ...opts() });
    expect(JSON.stringify(await get(PERSIST_KEY))).not.toContain("hunter2");
  });

  it("scopes by user: B never hydrates A's blob, A restores", async () => {
    const a = new QueryClient();
    a.setQueryData(["feed"], "secretA");
    await persistQueryClientSave({ queryClient: a, ...opts("a") });
    const b = new QueryClient();
    await persistQueryClientRestore({ queryClient: b, ...opts("b") });
    expect(b.getQueryData(["feed"])).toBeUndefined();
    const a2 = new QueryClient();
    a.setQueryData(["feed"], "secretA");
    await persistQueryClientSave({ queryClient: a, ...opts("a") });
    await persistQueryClientRestore({ queryClient: a2, ...opts("a") });
    expect(a2.getQueryData(["feed"])).toBe("secretA");
  });

  it("no user: nothing persisted", async () => {
    const a = new QueryClient();
    a.setQueryData(["feed"], 1);
    await persistQueryClientSave({
      queryClient: a,
      ...persistOptionsFor(null),
    });
    expect(await get(PERSIST_KEY)).toBeUndefined();
  });
});
