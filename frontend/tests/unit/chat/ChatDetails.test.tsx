/**
 * @file tests/unit/chat/ChatDetails.test.tsx
 * @brief Details panel sections hide when empty; slide-over a11y; starters.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GroupDetails } from "@/components/chat/details/GroupDetails";
import { PersonDetails } from "@/components/chat/details/PersonDetails";
import { DetailsHost } from "@/components/chat/chat-layout/DetailsHost";
import {
  ConversationStarters,
  buildStarters,
} from "@/components/chat/ConversationStarters";
import type { DmContext, GroupContext } from "@/lib/api/chatContext";

vi.mock("@/stores/presence", () => ({
  useOnline: () => false,
  usePresenceStore: (sel: (s: { online: Record<string, true> }) => unknown) =>
    sel({ online: {} }),
  watchPresence: vi.fn(),
  unwatchPresence: vi.fn(),
}));
vi.mock("@/hooks/useActivePrompts", () => ({
  useActivePrompts: () => ({
    data: [{ prompt: { prompt_type: "daily_question", title: "Best meal?" } }],
  }),
}));
vi.mock("@/hooks/useChatContext", () => ({
  useChatContext: () => ({ isLoading: false, isError: true, data: undefined }),
}));

const dm: DmContext = {
  kind: "dm",
  peer: {
    id: "p",
    display_name: "Leo Soto",
    username: "leo",
    avatar_url: null,
    last_seen_at: null,
    local_time_tz: null,
    birthday_in_days: 3,
  },
  shared_groups: [],
  upcoming_events: [
    { id: "e", title: "BBQ", starts_at: "2026-11-29T18:00:00Z" },
  ],
};
const group: GroupContext = {
  kind: "group",
  members: [{ id: "a", display_name: "Ann", avatar_url: null }],
  member_count: 1,
  next_event: null,
  open_lists: [],
};

describe("details", () => {
  it("person hides empty sections and shows birthday", () => {
    render(<PersonDetails ctx={dm} />);
    expect(screen.getByText("Birthday in 3 days")).toBeInTheDocument();
    expect(screen.getByText("Upcoming events together")).toBeInTheDocument();
    expect(screen.queryByText("Shared groups")).toBeNull();
    expect(screen.queryByText("Shared photos")).toBeNull();
  });
  it("group hides empty sections", () => {
    render(<GroupDetails ctx={group} />);
    expect(screen.getByText("1 member")).toBeInTheDocument();
    expect(screen.queryByText("Next event")).toBeNull();
    expect(screen.queryByText("Open lists")).toBeNull();
  });
});

describe("DetailsHost slide-over", () => {
  it("traps focus in a dialog, Esc closes, focus returns to toggle", async () => {
    const onClose = vi.fn();
    function Wrap() {
      const [open, setOpen] = React.useState(false);
      return (
        <>
          <button id="chat-details-toggle" onClick={() => setOpen(true)}>
            toggle
          </button>
          <DetailsHost
            channelId="c"
            inline={false}
            open={open}
            onClose={() => {
              onClose();
              setOpen(false);
            }}
          />
        </>
      );
    }
    render(<Wrap />);
    const toggle = screen.getByText("toggle");
    toggle.focus();
    fireEvent.click(toggle);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog.contains(document.activeElement)).toBe(true);
    fireEvent.keyDown(document.activeElement ?? dialog, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(toggle));
  });
});

describe("starters", () => {
  it("builds daily, event and birthday chips, max 3, with photo fallback", () => {
    const s = buildStarters("Best meal?", dm);
    expect(s.map((x) => x.label)).toEqual([
      "Answer today's question together",
      "Plan for BBQ",
      "Leo's birthday is in 3 days",
    ]);
    expect(buildStarters(null, group)[0]?.label).toBe("Share a photo");
  });
  it("prefills on click and hides at 5 messages", () => {
    const onPick = vi.fn();
    const qc = new QueryClient();
    const { rerender } = render(
      <QueryClientProvider client={qc}>
        <ConversationStarters messageCount={1} onPick={onPick} />
      </QueryClientProvider>,
    );
    fireEvent.click(screen.getByText("Answer today's question together"));
    expect(onPick).toHaveBeenCalledWith("Best meal? ");
    rerender(
      <QueryClientProvider client={qc}>
        <ConversationStarters messageCount={5} onPick={onPick} />
      </QueryClientProvider>,
    );
    expect(screen.queryByRole("list")).toBeNull();
  });
});
