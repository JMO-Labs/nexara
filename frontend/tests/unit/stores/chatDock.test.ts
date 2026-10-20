/**
 * @file tests/unit/stores/chatDock.test.ts
 * @brief Unit tests for chatDock Zustand store.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock sessionStorage before importing the store
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(global, "sessionStorage", {
  value: sessionStorageMock,
  writable: true,
});

// Import after mock is set up
import { useChatDock } from "@/stores/chatDock";

describe("chatDock store", () => {
  beforeEach(() => {
    sessionStorageMock.clear();
    sessionStorageMock.getItem.mockClear();
    sessionStorageMock.setItem.mockClear();
    // Reset store to initial state
    useChatDock.setState({
      openThreadIds: [],
      minimized: {},
      launcherOpen: false,
      unreadCount: 0,
    });
  });

  describe("openThread", () => {
    it("appends a thread id", () => {
      useChatDock.getState().openThread("t1");
      expect(useChatDock.getState().openThreadIds).toEqual(["t1"]);
    });

    it("deduplicates — opening same id twice keeps one entry", () => {
      useChatDock.getState().openThread("t1");
      useChatDock.getState().openThread("t1");
      expect(useChatDock.getState().openThreadIds).toEqual(["t1"]);
    });

    it("caps at 3 threads on desktop", () => {
      useChatDock.getState().openThread("t1");
      useChatDock.getState().openThread("t2");
      useChatDock.getState().openThread("t3");
      useChatDock.getState().openThread("t4");
      expect(useChatDock.getState().openThreadIds).toHaveLength(3);
      // oldest (t1) should be evicted
      expect(useChatDock.getState().openThreadIds).not.toContain("t1");
      expect(useChatDock.getState().openThreadIds).toContain("t4");
    });

    it("writes openThreadIds to sessionStorage", () => {
      useChatDock.getState().openThread("t1");
      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        "chatDock.openThreadIds",
        JSON.stringify(["t1"]),
      );
    });
  });

  describe("closeThread", () => {
    it("removes a thread id", () => {
      useChatDock.getState().openThread("t1");
      useChatDock.getState().openThread("t2");
      useChatDock.getState().closeThread("t1");
      expect(useChatDock.getState().openThreadIds).toEqual(["t2"]);
    });

    it("removes minimized entry when closing", () => {
      useChatDock.getState().openThread("t1");
      useChatDock.getState().toggleMinimize("t1");
      useChatDock.getState().closeThread("t1");
      expect(useChatDock.getState().minimized["t1"]).toBeUndefined();
    });

    it("writes updated openThreadIds to sessionStorage", () => {
      useChatDock.getState().openThread("t1");
      sessionStorageMock.setItem.mockClear();
      useChatDock.getState().closeThread("t1");
      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        "chatDock.openThreadIds",
        JSON.stringify([]),
      );
    });
  });

  describe("toggleMinimize", () => {
    it("sets minimized true when not present", () => {
      useChatDock.getState().toggleMinimize("t1");
      expect(useChatDock.getState().minimized["t1"]).toBe(true);
    });

    it("flips true -> false", () => {
      useChatDock.getState().toggleMinimize("t1");
      useChatDock.getState().toggleMinimize("t1");
      expect(useChatDock.getState().minimized["t1"]).toBe(false);
    });

    it("flips false -> true", () => {
      useChatDock.setState({ minimized: { t1: false } });
      useChatDock.getState().toggleMinimize("t1");
      expect(useChatDock.getState().minimized["t1"]).toBe(true);
    });
  });

  describe("setLauncherOpen", () => {
    it("updates launcherOpen", () => {
      useChatDock.getState().setLauncherOpen(true);
      expect(useChatDock.getState().launcherOpen).toBe(true);
      useChatDock.getState().setLauncherOpen(false);
      expect(useChatDock.getState().launcherOpen).toBe(false);
    });
  });

  describe("setUnreadCount", () => {
    it("updates unreadCount", () => {
      useChatDock.getState().setUnreadCount(5);
      expect(useChatDock.getState().unreadCount).toBe(5);
    });
  });
});
