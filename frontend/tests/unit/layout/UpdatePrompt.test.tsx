/**
 * @file tests/unit/layout/UpdatePrompt.test.tsx
 * @brief Waiting SW => toast with Reload that posts SKIP_WAITING.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render } from "@testing-library/react";
import UpdatePrompt from "@/components/layout/UpdatePrompt";
import { useToasts } from "@/stores/toasts";

describe("UpdatePrompt", () => {
  afterEach(() => {
    delete (navigator as any).serviceWorker;
    useToasts.getState().clear();
  });

  it("offers Reload and posts SKIP_WAITING", async () => {
    const postMessage = vi.fn();
    const swAdd = vi.fn();
    const reg = { waiting: { postMessage }, addEventListener: vi.fn() };
    Object.defineProperty(navigator, "serviceWorker", {
      value: {
        getRegistration: vi.fn().mockResolvedValue(reg),
        addEventListener: swAdd,
      },
      configurable: true,
    });
    render(<UpdatePrompt />);
    await vi.waitFor(() => expect(useToasts.getState().items).toHaveLength(1));
    const t = useToasts.getState().items[0];
    expect(t.message).toBe("New version available");
    expect(t.action?.label).toBe("Reload");
    t.action!.onClick();
    t.action!.onClick();
    expect(postMessage).toHaveBeenCalledTimes(1);
    expect(swAdd).toHaveBeenCalledTimes(1);
    expect(swAdd.mock.calls[0][2]).toEqual({ once: true });
    expect(postMessage).toHaveBeenCalledWith({ type: "SKIP_WAITING" });
  });
});
