/**
 * @file tests/unit/hooks/useHomeLayout.test.tsx
 * @brief Unit tests for useHomeLayout hook (react-grid-layout shape).
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

import * as settingsApi from "@/lib/api/settings";
import * as homeApi from "@/lib/api/home";
import { useHomeLayout } from "@/hooks/useHomeLayout";
import type { WidgetInstance } from "@/lib/widgets/registry";

vi.mock("@/lib/api/settings");
vi.mock("@/lib/api/home");

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  Wrapper.displayName = "Wrapper";
  return { Wrapper, qc };
}

function makeWidget(overrides: Partial<WidgetInstance> = {}): WidgetInstance {
  return {
    id: "w-1",
    defId: "feed",
    x: 0,
    y: 0,
    w: 8,
    h: 4,
    collapsed: false,
    ...overrides,
  };
}

function mockSettings(home_layout: { widgets: WidgetInstance[] } | null) {
  vi.mocked(settingsApi.getSettings).mockResolvedValue({
    home_layout,
  } as unknown as ReturnType<
    typeof settingsApi.getSettings
  > extends Promise<infer T>
    ? T
    : never);
}

describe("useHomeLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(homeApi.putHomeLayout).mockResolvedValue(
      {} as ReturnType<typeof homeApi.putHomeLayout> extends Promise<infer T>
        ? T
        : never,
    );
  });

  it("returns default layout (6 widgets) when settings empty", async () => {
    mockSettings(null);
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.widgets.length).toBe(6);
    expect(result.current.widgets[0].defId).toBe("feed");
    expect(result.current.widgets[0].w).toBeGreaterThan(0);
  });

  it("returns persisted widgets when home_layout is set", async () => {
    const persisted: WidgetInstance[] = [makeWidget()];
    mockSettings({ widgets: persisted });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.widgets[0].defId).toBe("feed");
    expect(result.current.widgets[0].w).toBe(8);
  });

  it("addWidget appends a widget with default size from registry def", async () => {
    mockSettings({ widgets: [makeWidget({ id: "existing" })] });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.addWidget("activity");
    });
    await waitFor(() =>
      expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1),
    );
    const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
    expect(call.widgets).toHaveLength(2);
    expect(call.widgets[1].defId).toBe("activity");
    expect(call.widgets[1].w).toBeGreaterThan(0);
  });

  it("removeWidget drops the target widget", async () => {
    const w1 = makeWidget({ id: "w-1" });
    const w2 = makeWidget({ id: "w-2", defId: "activity" });
    mockSettings({ widgets: [w1, w2] });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    act(() => {
      result.current.removeWidget("w-1");
    });
    await waitFor(() =>
      expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1),
    );
    const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
    expect(call.widgets).toHaveLength(1);
    expect(call.widgets[0].id).toBe("w-2");
  });

  it("toggleCollapsed flips state", async () => {
    mockSettings({ widgets: [makeWidget({ collapsed: false })] });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    act(() => {
      result.current.toggleCollapsed("w-1");
    });
    await waitFor(() =>
      expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1),
    );
    const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
    expect(call.widgets[0].collapsed).toBe(true);
  });

  it("applyLayout updates x/y/w/h on matching ids", async () => {
    mockSettings({ widgets: [makeWidget()] });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    act(() => {
      result.current.applyLayout([{ i: "w-1", x: 4, y: 2, w: 6, h: 5 }]);
    });
    await waitFor(() =>
      expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1),
    );
    const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
    expect(call.widgets[0].x).toBe(4);
    expect(call.widgets[0].w).toBe(6);
  });

  it("resetToDefault writes the default layout", async () => {
    mockSettings({ widgets: [makeWidget()] });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    act(() => {
      result.current.resetToDefault();
    });
    await waitFor(() =>
      expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1),
    );
    const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
    expect(call.widgets).toHaveLength(6);
  });

  it("normalises legacy size+order rows to x/y/w/h", async () => {
    const legacy = [
      { id: "a", defId: "feed", size: "lg", order: 0, collapsed: false },
      { id: "b", defId: "activity", size: "sm", order: 1, collapsed: false },
    ] as unknown as WidgetInstance[];
    mockSettings({ widgets: legacy });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.widgets[0]).toMatchObject({
      id: "a",
      defId: "feed",
      w: 8,
    });
    expect(result.current.widgets[1]).toMatchObject({ id: "b", defId: "activity" });
  });
});
