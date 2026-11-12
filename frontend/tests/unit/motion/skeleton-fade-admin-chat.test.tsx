/**
 * @file tests/unit/motion/skeleton-fade-admin-chat.test.tsx
 * @brief AdminLoading (all admin tabs) and ChannelList skeletons fade in;
 *        reduced motion skips the fade.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

let reduced = false;
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: () => reduced };
});

import { AdminLoading } from "@/components/admin/AdminState";
import { ChannelList } from "@/components/chat/ChannelList";

const chat = () => (
  <ChannelList
    channels={[]}
    dms={[]}
    activeId={null}
    unread={{}}
    onSelect={vi.fn()}
    loading
  />
);

beforeEach(() => {
  reduced = false;
});

describe("AdminLoading fade", () => {
  it("fades in", () => {
    render(<AdminLoading />);
    expect(screen.getByTestId("admin-loading")).toHaveStyle({ opacity: "0" });
  });
  it("skips under reduced motion", () => {
    reduced = true;
    render(<AdminLoading />);
    expect(screen.getByTestId("admin-loading").style.opacity).toBe("");
  });
});

describe("ChannelList skeleton fade", () => {
  it("fades in", () => {
    render(chat());
    expect(screen.getByTestId("channel-skeleton")).toHaveStyle({
      opacity: "0",
    });
  });
  it("skips under reduced motion", () => {
    reduced = true;
    render(chat());
    expect(screen.getByTestId("channel-skeleton").style.opacity).toBe("");
  });
});
