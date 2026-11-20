/**
 * @file tests/unit/home/tiles/ChatsTile.test.tsx
 * @brief ChatsTile: thread list, accordion, inline reply, empty/scope states.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/app",
}));
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../../utils/renderWithProviders";
import type { HomeChatThread } from "@/lib/api/home";

const mocks = vi.hoisted(() => ({
  chats: { data: { items: [] as unknown[] } } as {
    data: { items: unknown[] } | undefined;
  },
  send: vi.fn(),
  optimistic: vi.fn(),
  markRead: vi.fn(() => Promise.resolve()),
}));

vi.mock("@/hooks/useHomeChats", () => ({
  useHomeChats: () => mocks.chats,
}));
vi.mock("@/hooks/useChat", () => ({
  useMessages: (id: string) => ({
    data: {
      pages: [
        {
          items: [
            {
              id: `${id}-4`,
              content: "newest",
              author: { id: "u2", display_name: "Ruth" },
              created_at: "2026-11-19T10:04:00Z",
            },
            {
              id: `${id}-3`,
              content: "third",
              author: { id: "me", display_name: "Ana" },
              created_at: "2026-11-19T10:03:00Z",
            },
            {
              id: `${id}-2`,
              content: "second",
              author: { id: "u2", display_name: "Ruth" },
              created_at: "2026-11-19T10:02:00Z",
            },
            {
              id: `${id}-1`,
              content: "oldest",
              author: { id: "u2", display_name: "Ruth" },
              created_at: "2026-11-19T10:01:00Z",
            },
          ],
        },
      ],
    },
  }),
  sendChatMessage: mocks.send,
  optimisticAddMessage: mocks.optimistic,
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({
    data: [{ id: "g9", name: "Soccer parents" }],
  }),
}));
vi.mock("@/lib/api/chat", () => ({ markChannelRead: mocks.markRead }));

import { ChatsTile } from "@/components/home/tiles/ChatsTile";
import { useHomeScope } from "@/stores/homeScope";
import { useSession } from "@/stores/session";

function thread(over: Partial<HomeChatThread>): HomeChatThread {
  return {
    channel_id: "c1",
    name: "Family",
    channel_type: "subgroup",
    subgroup_id: "g1",
    peer: null,
    last_message: {
      id: "m1",
      author_name: "Ruth",
      content: "Green beans?",
      created_at: "2026-11-19T10:00:00Z",
    },
    unread_count: 0,
    mentions_me: false,
    last_activity_at: "2026-11-19T10:00:00Z",
    ...over,
  };
}

const TWO = [
  thread({ channel_id: "c1", name: "Family", unread_count: 3 }),
  thread({
    channel_id: "c2",
    name: "Book club",
    subgroup_id: "g2",
    mentions_me: true,
  }),
];

beforeEach(() => {
  vi.clearAllMocks();
  useHomeScope.setState({ scope: "all" });
  useSession.setState({ user: { id: "me" } as never });
  mocks.chats = { data: { items: TWO } };
});

const row = (name: string) =>
  screen.getByRole("button", { name: new RegExp(`^${name}`) });

describe("ChatsTile", () => {
  it("renders threads in API order with first open", () => {
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    const rows = screen.getAllByRole("button", { name: /^(Family|Book club)/ });
    expect(rows.map((r) => r.textContent)).toEqual([
      expect.stringContaining("Family"),
      expect.stringContaining("Book club"),
    ]);
    expect(row("Family")).toHaveAttribute("aria-expanded", "true");
    expect(row("Book club")).toHaveAttribute("aria-expanded", "false");
  });

  it("shows newest 3 messages oldest to newest", () => {
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    expect(screen.queryByText("oldest")).toBeNull();
    const texts = ["second", "third", "newest"].map((t) => screen.getByText(t));
    expect(
      texts[0].compareDocumentPosition(texts[2]) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("opens second row, collapses first, marks read", () => {
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    fireEvent.click(row("Book club"));
    expect(row("Book club")).toHaveAttribute("aria-expanded", "true");
    expect(row("Family")).toHaveAttribute("aria-expanded", "false");
    expect(mocks.markRead).toHaveBeenCalledWith("c2");
  });

  it("sends reply, marks read, clears input", async () => {
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    const input = screen.getByLabelText("Reply to Family");
    fireEvent.change(input, { target: { value: "On my way" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(mocks.optimistic).toHaveBeenCalled();
    expect(mocks.send).toHaveBeenCalledWith("c1", "On my way");
    await waitFor(() => expect(mocks.markRead).toHaveBeenCalledWith("c1"));
    expect(input).toHaveValue("");
  });

  it("ignores empty reply", () => {
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    fireEvent.change(screen.getByLabelText("Reply to Family"), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(mocks.send).not.toHaveBeenCalled();
  });

  it("shows empty state with start link", () => {
    mocks.chats = { data: { items: [] } };
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    expect(screen.getByText("No chats yet")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Start a chat" }),
    ).toBeInTheDocument();
  });

  it("filters by scope and shows nothing-from state; DMs only in all", () => {
    mocks.chats = {
      data: {
        items: [
          ...TWO,
          thread({
            channel_id: "c3",
            name: "Sam",
            channel_type: "direct",
            subgroup_id: null,
          }),
        ],
      },
    };
    useHomeScope.setState({ scope: "g2" });
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    expect(screen.queryByRole("button", { name: /^Family/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Sam/ })).toBeNull();
    expect(row("Book club")).toBeInTheDocument();
  });

  it("shows nothing-from message when scope has no threads", () => {
    useHomeScope.setState({ scope: "g9" });
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    expect(
      screen.getByText("Nothing from Soccer parents yet"),
    ).toBeInTheDocument();
  });

  it("phone header shows summed unread count and hot", () => {
    renderWithProviders(<ChatsTile open={false} onToggle={() => {}} />);
    expect(screen.getByLabelText("3 need you")).toBeInTheDocument();
    expect(screen.getAllByText("Ruth: Green beans?").length).toBeGreaterThan(0);
  });

  it("links to all chats", () => {
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    for (const l of screen.getAllByRole("link", { name: "See all chats" }))
      expect(l).toHaveAttribute("href", "/app/chat");
  });

  it("caps the thread list height and does not stretch the inline thread", () => {
    renderWithProviders(<ChatsTile open onToggle={() => {}} />);
    const list = row("Family").closest("ul") as HTMLElement;
    expect(list.className).toContain("max-h-[420px]");
    // Rows must not shrink, or the open thread overlaps the next row.
    expect(list.className).toContain("[&>li]:shrink-0");
    expect(list.className).not.toContain("flex-1");
    const inline = screen.getByRole("textbox", { name: /reply to family/i });
    const root = inline.closest("form")!.parentElement as HTMLElement;
    expect(root.className).not.toContain("flex-1");
  });
});
