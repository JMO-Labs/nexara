/**
 * @file tests/unit/components/home/WidgetColumn.test.tsx
 * @brief Unit tests for WidgetColumn (ordering, keyboard reorder, customize).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

const state = {
  order: ["upcoming-events", "my-groups", "media", "quick-actions"],
  hidden: [] as string[],
};
const move = vi.fn();
const toggle = vi.fn();
vi.mock("@/hooks/useHomeLayout", () => ({
  useHomeLayout: () => ({ ...state, move, toggle }),
}));
vi.mock("@/components/home/widgetRegistry", () => ({
  WIDGETS: [
    ["upcoming-events", "Upcoming events"],
    ["my-groups", "My groups"],
    ["media", "Media"],
    ["quick-actions", "Quick actions"],
  ].map(([id, title]) => ({
    id,
    title,
    Component: () => <p>{`body ${id}`}</p>,
  })),
}));

import { WidgetColumn } from "@/components/home/WidgetColumn";

const origRect = Element.prototype.getBoundingClientRect;
beforeEach(() => {
  state.order = ["upcoming-events", "my-groups", "media", "quick-actions"];
  state.hidden = [];
  vi.clearAllMocks();
  // jsdom has no layout; give sortable items stacked rects so dnd-kit's
  // keyboard coordinates can find the next item.
  Element.prototype.getBoundingClientRect = function () {
    const el = this as HTMLElement;
    const i = Number(el.getAttribute("data-index") ?? -1);
    const top = i < 0 ? 0 : i * 100;
    return {
      top,
      left: 0,
      right: 200,
      bottom: top + 90,
      width: 200,
      height: 90,
      x: 0,
      y: top,
      toJSON() {},
    } as DOMRect;
  };
});
afterEach(() => {
  Element.prototype.getBoundingClientRect = origRect;
});

describe("WidgetColumn", () => {
  it("renders visible widgets in order inside a labelled aside", () => {
    render(<WidgetColumn />);
    const aside = screen.getByRole("complementary", { name: "Widgets" });
    const titles = within(aside)
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent);
    expect(titles).toEqual([
      "Upcoming events",
      "My groups",
      "Media",
      "Quick actions",
    ]);
  });

  it("omits hidden widgets and re-shows via Customize", async () => {
    state.hidden = ["media"];
    render(<WidgetColumn />);
    expect(screen.queryByText("body media")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Customize" }));
    await userEvent.click(
      await screen.findByRole("menuitemcheckbox", { name: "Media" }),
    );
    expect(toggle).toHaveBeenCalledWith("media");
  });

  it("reorders with the keyboard (space, arrow down, space)", async () => {
    render(<WidgetColumn />);
    const handle = screen.getByRole("button", {
      name: "Reorder Upcoming events",
    });
    handle.focus();
    await userEvent.keyboard(" ");
    await userEvent.keyboard("{ArrowDown}");
    await userEvent.keyboard(" ");
    expect(move).toHaveBeenCalledWith(0, 1);
  });
});
