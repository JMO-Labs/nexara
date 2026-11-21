/**
 * @file tests/unit/motion/skeleton-fade.test.tsx
 * @brief MessageList skeleton states fade; reduced motion skips it.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

let reduced = false;
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: () => reduced };
});
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));
import { MessageList } from "@/components/chat/MessageList";

beforeEach(() => {
  reduced = false;
});

describe("MessageList skeleton fade", () => {
  const list = () => (
    <MessageList
      messages={[]}
      isLoading
      hasMore={false}
      isFetchingMore={false}
      onLoadMore={vi.fn()}
    />
  );
  it("fades skeleton in", () => {
    render(list());
    expect(screen.getByTestId("message-skeleton")).toHaveStyle({
      opacity: "0",
    });
  });
  it("skips under reduced motion", () => {
    reduced = true;
    render(list());
    expect(screen.getByTestId("message-skeleton").style.opacity).toBe("");
  });
});
