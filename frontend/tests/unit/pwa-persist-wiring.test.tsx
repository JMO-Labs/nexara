/**
 * @file tests/unit/pwa-persist-wiring.test.tsx
 * @brief Real Providers + session store: query cache persists/restores per
 *        signed-in user, never leaks across users, purges on logout.
 */
import "fake-indexeddb/auto";
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, act, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, useQuery } from "@tanstack/react-query";
import { persistQueryClientSave } from "@tanstack/react-query-persist-client";
import { get } from "idb-keyval";
import Providers from "@/app/providers";
import { useSession } from "@/stores/session";
import {
  PERSIST_BUSTER,
  PERSIST_KEY,
  clearPersistedQueries,
  persistOptionsFor,
} from "@/lib/pwa/queryPersist";

vi.mock("@/lib/plugins/plugin-loader", () => ({ loadPlugins: vi.fn() }));

type Blob = {
  buster: string;
  clientState: { queries: { queryKey: unknown[]; state: { data: unknown } }[] };
};
const blob = async () => {
  const raw = await get<string>(PERSIST_KEY);
  return raw ? (JSON.parse(raw) as Blob) : undefined;
};
const user = (id: string) => ({ id }) as never;
const seed = async (id: string, data: string) => {
  const qc = new QueryClient();
  qc.setQueryData(["feed"], data);
  await persistQueryClientSave({ queryClient: qc, ...persistOptionsFor(id) });
};

/** Renders the feed query; logs "<user>:<data>" for every render. */
const seen: string[] = [];
function Feed({ fn }: { fn: () => Promise<string> }) {
  const uid = useSession((s) => s.user?.id);
  const { data } = useQuery({
    queryKey: ["feed"],
    queryFn: fn,
    enabled: !!uid,
  });
  seen.push(`${uid}:${data}`);
  return <p data-testid="feed">{data ?? "none"}</p>;
}
const mount = (fn: () => Promise<string>) =>
  render(
    <Providers>
      <Feed fn={fn} />
    </Providers>,
  );

afterEach(async () => {
  cleanup();
  seen.length = 0;
  useSession.setState({ user: null, status: "idle" });
  await clearPersistedQueries();
});

describe("Providers query persistence wiring", () => {
  it("(a) persists a successful query under BUILD_ID:userId", async () => {
    // Session user is null at mount and arrives later (real boot order).
    mount(async () => "dataA");
    await act(() => new Promise((r) => setTimeout(r, 50)));
    act(() => useSession.getState().setUser(user("A")));
    expect(await screen.findByText("dataA")).toBeInTheDocument();
    await waitFor(
      async () => {
        const b = await blob();
        expect(b?.buster).toBe(`${PERSIST_BUSTER}:A`);
        expect(b?.clientState.queries[0]?.state.data).toBe("dataA");
      },
      { timeout: 4000 },
    );
  }, 10_000);

  it("(b) restores the signed-in user's cache without fetching", async () => {
    await seed("A", "cachedA");
    useSession.setState({ user: user("A"), status: "authenticated" });
    const fn = vi.fn(async () => "fresh");
    mount(fn);
    expect(await screen.findByText("cachedA")).toBeInTheDocument();
    expect(fn).not.toHaveBeenCalled();
  });

  it("(c) switching to B never shows A's data and persists as B", async () => {
    await seed("A", "secretA");
    useSession.setState({ user: user("A"), status: "authenticated" });
    mount(async () =>
      useSession.getState().user?.id === "B" ? "dataB" : "secretA",
    );
    expect(await screen.findByText("secretA")).toBeInTheDocument();
    act(() => useSession.getState().setUser(user("B")));
    expect(await screen.findByText("dataB")).toBeInTheDocument();
    expect(seen).not.toContain("B:secretA");
    await waitFor(
      async () => {
        const b = await blob();
        expect(b?.buster).toBe(`${PERSIST_BUSTER}:B`);
        expect(JSON.stringify(b)).not.toContain("secretA");
      },
      { timeout: 4000 },
    );
  }, 10_000);

  it("(d) logout leaves IndexedDB empty (no late throttled write)", async () => {
    act(() => useSession.getState().setUser(user("A")));
    mount(async () => "dataA");
    expect(await screen.findByText("dataA")).toBeInTheDocument();
    await waitFor(async () => expect(await blob()).toBeDefined(), {
      timeout: 4000,
    });
    act(() => useSession.getState().setUser(null));
    await new Promise((r) => setTimeout(r, 2500));
    expect(await get(PERSIST_KEY)).toBeUndefined();
    expect(screen.getByTestId("feed")).not.toHaveTextContent("dataA");
  }, 10_000);

  it("(e) a restore finishing after a user change is ignored", async () => {
    await seed("A", "secretA");
    useSession.setState({ user: user("A"), status: "authenticated" });
    mount(async () => "dataB");
    // Switch before A's restore resolves; no purge, so A's blob is still read.
    act(() => useSession.setState({ user: user("B") }));
    expect(await screen.findByText("dataB")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 100));
    expect(screen.getByTestId("feed")).toHaveTextContent("dataB");
    expect(seen).not.toContain("B:secretA");
  });
});
