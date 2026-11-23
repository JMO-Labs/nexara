/**
 * @file tests/unit/chat/ConversationHeader.test.tsx
 * @brief Header: presence line, "/" search focus, Esc clears, live count,
 *        details toggle ARIA.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConversationHeader } from "@/components/chat/chat-layout/ConversationHeader";
import { MessageItem } from "@/components/chat/MessageItem";
import type { ChatContext } from "@/lib/api/chatContext";

vi.mock("@/stores/presence", () => ({
  useOnline: () => true,
  usePresenceStore: (sel: (s: { online: Record<string, true> }) => unknown) =>
    sel({ online: { a: true } }),
  watchPresence: vi.fn(),
  unwatchPresence: vi.fn(),
}));

const group: ChatContext = {
  kind: "group",
  members: [
    { id: "a", display_name: "A", avatar_url: null },
    { id: "b", display_name: "B", avatar_url: null },
  ],
  member_count: 12,
  next_event: null,
  open_lists: [],
};

function Harness({ ctx }: { ctx?: ChatContext }) {
  const [q, setQ] = React.useState("");
  return (
    <>
      <input aria-label="Message" />
      <ConversationHeader
        title="Soto"
        color="red"
        context={ctx}
        onBack={() => {}}
        query={q}
        onQuery={setQ}
        matchCount={3}
        compact={false}
        onToggleDensity={() => {}}
        detailsOpen={true}
        onToggleDetails={() => {}}
      />
    </>
  );
}

describe("ConversationHeader", () => {
  it("shows the group presence line", () => {
    render(<Harness ctx={group} />);
    expect(screen.getByText("12 members · 1 online")).toBeInTheDocument();
  });

  it("shows DM presence with local time", () => {
    render(
      <Harness
        ctx={{
          kind: "dm",
          peer: {
            id: "p",
            display_name: "Leo Soto",
            username: "leo",
            avatar_url: null,
            last_seen_at: null,
            local_time_tz: "UTC",
            birthday_in_days: null,
          },
          shared_groups: [],
          upcoming_events: [],
        }}
      />,
    );
    expect(screen.getByText(/^Online · .* for Leo$/)).toBeInTheDocument();
  });

  it("'/' focuses search unless typing in another field; Esc clears", () => {
    render(<Harness />);
    const search = screen.getByLabelText("Search in conversation");
    const other = screen.getByLabelText("Message");
    other.focus();
    fireEvent.keyDown(other, { key: "/" });
    expect(document.activeElement).toBe(other);
    (document.body as HTMLElement).focus();
    fireEvent.keyDown(document.body, { key: "/" });
    expect(document.activeElement).toBe(search);
    fireEvent.change(search, { target: { value: "bbq" } });
    expect(screen.getByRole("status")).toHaveTextContent("3 matches");
    fireEvent.keyDown(search, { key: "Escape" });
    expect(search).toHaveValue("");
    expect(screen.getByRole("status")).toHaveTextContent("");
  });

  it("details toggle exposes aria-expanded and aria-controls", () => {
    render(<Harness />);
    const btn = screen.getByRole("button", { name: "Close details" });
    expect(btn).toHaveAttribute("aria-expanded", "true");
    expect(btn).toHaveAttribute("aria-controls", "chat-details");
  });
});

describe("MessageItem highlight", () => {
  it("wraps matches in <mark>", () => {
    const { container } = render(
      <MessageItem
        message={{
          id: "m1",
          channel_id: "c",
          author: null,
          content: "Bring the BBQ sauce",
          edited_at: null,
          deleted: false,
          created_at: "2026-11-22T10:00:00Z",
        }}
        highlight="bbq"
      />,
    );
    expect(container.querySelector("mark")?.textContent).toBe("BBQ");
  });
});
