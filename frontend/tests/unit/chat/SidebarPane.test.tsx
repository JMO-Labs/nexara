/**
 * @file tests/unit/chat/SidebarPane.test.tsx
 * @brief Search + All/Groups/Direct filtering and ink "New message" button.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SidebarPane } from "@/components/chat/chat-layout/SidebarPane";

const base = {
  channels: [
    {
      id: "c1",
      name: "general",
      channel_type: "community" as const,
      subgroup_id: null,
      created_at: "",
    },
  ],
  dms: [
    {
      channel_id: "d1",
      peer: {
        id: "u1",
        username: "alex",
        display_name: "Alex",
        avatar_url: null,
      },
      created_at: "",
    },
  ],
  activeId: null,
  unread: {},
  onSelect: () => {},
  muted: false,
  onToggleMute: () => {},
  onNewDm: () => {},
};

describe("SidebarPane", () => {
  it("filters threads with the search field", () => {
    render(<SidebarPane {...base} />);
    fireEvent.change(screen.getByLabelText("Search conversations"), {
      target: { value: "gen" },
    });
    expect(screen.getByText(/# general/)).toBeInTheDocument();
    expect(screen.queryByText("Alex")).toBeNull();
  });

  it("filters with the Segmented control", () => {
    render(<SidebarPane {...base} />);
    fireEvent.click(screen.getByRole("radio", { name: "Direct" }));
    expect(screen.queryByText(/# general/)).toBeNull();
    expect(screen.getByText("Alex")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "Groups" }));
    expect(screen.getByText(/# general/)).toBeInTheDocument();
    expect(screen.queryByText("Alex")).toBeNull();
    fireEvent.click(screen.getByRole("radio", { name: "All" }));
    expect(screen.getByText("Alex")).toBeInTheDocument();
  });

  it("has a glass aside and an ink New message pill", () => {
    const onNewDm = vi.fn();
    render(<SidebarPane {...base} onNewDm={onNewDm} />);
    expect(screen.getByLabelText("Conversations").className).toMatch(/glass/);
    const btn = screen.getByRole("button", { name: /new message/i });
    expect(btn.className).toMatch(/bg-surface-strong/);
    expect(btn.className).not.toMatch(/bg-accent/);
    fireEvent.click(btn);
    expect(onNewDm).toHaveBeenCalled();
  });
});
