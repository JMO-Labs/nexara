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
  createPersister,
  shouldPersist,
  clearPersistedQueries,
} from "@/lib/pwa/queryPersist";
import { clearUserCache } from "@/lib/pwa/clearUserCache";

const opts = () => ({
  persister: createPersister()!,
  maxAge: 86_400_000,
  buster: "t",
  dehydrateOptions: { shouldDehydrateQuery: shouldPersist },
});

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
});
