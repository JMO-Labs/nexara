/**
 * @file tests/unit/hooks/useHomeLayout.test.tsx
 * @brief Unit tests for useHomeLayout (ordered widget list + hidden ids).
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

import * as settingsApi from "@/lib/api/settings";
import * as homeApi from "@/lib/api/home";
import { useHomeLayout } from "@/hooks/useHomeLayout";

vi.mock("@/lib/api/settings");
vi.mock("@/lib/api/home");
vi.mock("@/lib/auth/session", () => ({ getAccessToken: () => "t" }));

const DEFAULT = ["upcoming-events", "my-groups", "media", "quick-actions"];

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const W = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  W.displayName = "W";
  return W;
}

function mockLayout(home_layout: unknown) {
  vi.mocked(settingsApi.getSettings).mockResolvedValue({
    home_layout,
  } as never);
}

async function setup(home_layout: unknown) {
  mockLayout(home_layout);
  const hook = renderHook(() => useHomeLayout(), { wrapper: wrapper() });
  await waitFor(() => expect(settingsApi.getSettings).toHaveBeenCalled());
  await act(async () => {}); // let the settings query resolve
  return hook;
}

describe("useHomeLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(homeApi.putHomeLayout).mockResolvedValue({} as never);
  });

  it("returns defaults for null layout", async () => {
    const { result } = await setup(null);
    expect(result.current.order).toEqual(DEFAULT);
    expect(result.current.hidden).toEqual([]);
  });

  it("returns defaults for legacy grid-shaped layout without crashing", async () => {
    const { result } = await setup({
      widgets: [{ id: "a", defId: "feed", x: 0, y: 0, w: 8, h: 4 }],
    });
    expect(result.current.order).toEqual(DEFAULT);
    expect(result.current.hidden).toEqual([]);
  });

  it("drops unknown ids and appends missing ids", async () => {
    mockLayout({ order: ["media", "bogus"], hidden: ["nope", "my-groups"] });
    const { result } = renderHook(() => useHomeLayout(), {
      wrapper: wrapper(),
    });
    await waitFor(() => expect(result.current.order[0]).toBe("media"));
    expect(result.current.order).toEqual([
      "media",
      "upcoming-events",
      "my-groups",
      "quick-actions",
    ]);
    expect(result.current.hidden).toEqual(["my-groups"]);
  });

  it("move updates order and PUTs once after 500ms debounce", async () => {
    const { result } = await setup(null);
    act(() => result.current.move(0, 2));
    await waitFor(() =>
      expect(result.current.order).toEqual([
        "my-groups",
        "media",
        "upcoming-events",
        "quick-actions",
      ]),
    );
    act(() => result.current.move(0, 1));
    await waitFor(() => expect(result.current.order[0]).toBe("media"));
    expect(homeApi.putHomeLayout).not.toHaveBeenCalled();
    await waitFor(() => expect(homeApi.putHomeLayout).toHaveBeenCalled());
    expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1);
    expect(homeApi.putHomeLayout).toHaveBeenCalledWith({
      order: ["media", "my-groups", "upcoming-events", "quick-actions"],
      hidden: [],
    });
  });

  it("toggle hides then shows a widget", async () => {
    const { result } = await setup(null);
    act(() => result.current.toggle("media"));
    await waitFor(() => expect(result.current.hidden).toEqual(["media"]));
    act(() => result.current.toggle("media"));
    await waitFor(() => expect(result.current.hidden).toEqual([]));
  });
});
