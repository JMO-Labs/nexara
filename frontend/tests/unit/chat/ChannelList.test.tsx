/**
 * @file tests/unit/chat/ChannelList.test.tsx
 * @brief Renders channels + DMs, highlights active, fires onSelect.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChannelList } from "@/components/chat/ChannelList";
import type { ChatChannel, DmThread } from "@/lib/api/chat";

function wrap(ui: React.ReactNode) {
  return render(<>{ui}</>);
}

const channels: ChatChannel[] = [
  {
    id: "c1",
    name: "general",
    channel_type: "community",
    subgroup_id: null,
    created_at: new Date().toISOString(),
  },
];
const dms: DmThread[] = [
  {
    channel_id: "d1",
    peer: {
      id: "u1",
      username: "alex",
      display_name: "Alex",
      avatar_url: null,
    },
    created_at: new Date().toISOString(),
  },
];

describe("ChannelList", () => {
  it("renders channels and DMs", () => {
    wrap(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId={null}
        unread={{}}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText(/# general/)).toBeInTheDocument();
    expect(screen.getByText("Alex")).toBeInTheDocument();
  });

  it("shows unread badge", () => {
    wrap(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId={null}
        unread={{ d1: 3 }}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("selects on click", () => {
    const onSelect = vi.fn();
    wrap(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId={null}
        unread={{}}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("Alex"));
    expect(onSelect).toHaveBeenCalledWith("d1");
  });

  it("marks the active row", () => {
    wrap(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId="d1"
        unread={{}}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("Alex").closest("button")).toHaveAttribute(
      "aria-current",
      "true",
    );
  });

  it("deletes a DM without selecting it", () => {
    const onSelect = vi.fn();
    const onDeleteDm = vi.fn();
    wrap(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId={null}
        unread={{}}
        onSelect={onSelect}
        onDeleteDm={onDeleteDm}
      />,
    );
    fireEvent.click(screen.getByLabelText("Delete conversation"));
    expect(onDeleteDm).toHaveBeenCalledWith("d1");
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("filters by query across channels and DMs", () => {
    wrap(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId={null}
        unread={{}}
        onSelect={() => {}}
        query="ale"
      />,
    );
    expect(screen.getByText("Alex")).toBeInTheDocument();
    expect(screen.queryByText(/# general/)).toBeNull();
  });

  it("shows only groups or only direct per segment", () => {
    const { rerender } = wrap(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId={null}
        unread={{}}
        onSelect={() => {}}
        segment="groups"
      />,
    );
    expect(screen.getByText(/# general/)).toBeInTheDocument();
    expect(screen.queryByText("Alex")).toBeNull();
    rerender(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId={null}
        unread={{}}
        onSelect={() => {}}
        segment="direct"
      />,
    );
    expect(screen.queryByText(/# general/)).toBeNull();
    expect(screen.getByText("Alex")).toBeInTheDocument();
  });

  it("shows an empty state when nothing matches", () => {
    wrap(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId={null}
        unread={{}}
        onSelect={() => {}}
        query="zzz"
      />,
    );
    expect(screen.getByText("No matches")).toBeInTheDocument();
  });

  it("renders selected rows with a soft ink tint, not bg-accent or a ring", () => {
    wrap(
      <ChannelList
        channels={channels}
        dms={dms}
        activeId="d1"
        unread={{}}
        onSelect={() => {}}
      />,
    );
    const cls = screen.getByText("Alex").closest("button")!.className;
    expect(cls).toMatch(/glass-item/);
    expect(cls).not.toMatch(/ring-ink/);
    expect(cls).toMatch(/color-mix/);
    expect(cls).not.toMatch(/bg-accent/);
  });
});

describe("ChannelList home-chats merge", () => {
  const thread = (id: string, at: string, unread: number) => ({
    channel_id: id,
    name: "x",
    channel_type: "direct" as const,
    subgroup_id: null,
    peer: null,
    last_message: {
      id: "m",
      author_name: "Richard",
      content: "he bud",
      created_at: at,
    },
    unread_count: unread,
    mentions_me: false,
    last_activity_at: at,
  });
  it("shows preview, unread badge and sections, newest first", () => {
    const two: DmThread[] = [
      ...dms,
      {
        channel_id: "d2",
        peer: {
          id: "u2",
          username: "bo",
          display_name: "Bo",
          avatar_url: null,
        },
        created_at: "",
      },
    ];
    wrap(
      <ChannelList
        channels={channels}
        dms={two}
        activeId={null}
        unread={{}}
        onSelect={() => {}}
        threads={{
          d1: thread("d1", "2026-11-20T10:00:00Z", 0),
          d2: thread("d2", "2026-11-22T10:00:00Z", 3),
        }}
      />,
    );
    expect(screen.getAllByText("Richard: he bud")).toHaveLength(2);
    expect(screen.getByLabelText("3 unread")).toBeInTheDocument();
    expect(screen.getByText("People")).toBeInTheDocument();
    expect(screen.getByText("Groups")).toBeInTheDocument();
    const names = screen.getAllByText(/^(Alex|Bo)$/).map((n) => n.textContent);
    expect(names).toEqual(["Bo", "Alex"]);
  });
});
