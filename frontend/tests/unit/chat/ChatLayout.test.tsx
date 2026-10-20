/**
 * @file tests/unit/chat/ChatLayout.test.tsx
 * @brief Phone/desktop pane switching and back button in ChatLayout.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));
vi.mock("@/hooks/useChat", () => ({
  useChannels: () => ({
    data: [
      {
        id: "c1",
        name: "general",
        channel_type: "community",
        subgroup_id: null,
        created_at: "",
      },
    ],
    isLoading: false,
  }),
  useDmThreads: () => ({ data: [], isLoading: false }),
  useMessages: () => ({
    data: { pages: [{ items: [] }] },
    isLoading: false,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
  }),
  useChatRealtime: () => ({
    typing: {},
    unread: {},
    markRead: vi.fn(),
    status: "open",
  }),
  useCreateDm: () => ({ mutateAsync: vi.fn() }),
  useDeleteDm: () => ({ mutateAsync: vi.fn() }),
  optimisticAddMessage: vi.fn(),
  sendChatMessage: vi.fn(),
  sendChatTyping: vi.fn(),
}));
vi.mock("@/lib/realtime/chat-ws", () => ({
  chatWs: { subscribe: () => () => {} },
}));

import { ChatLayout } from "@/components/chat/ChatLayout";

function wrap(activeId: string | null) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ChatLayout activeId={activeId} />
    </QueryClientProvider>,
  );
}

describe("ChatLayout", () => {
  it("shows only the list on phone when nothing is selected", () => {
    wrap(null);
    expect(screen.getByLabelText("Conversations").className).not.toMatch(
      /hidden/,
    );
    expect(screen.queryByLabelText("Back to channels")).toBeNull();
  });

  it("hides the list on phone and offers Back when a channel is open", () => {
    wrap("c1");
    expect(screen.getByLabelText("Conversations").className).toMatch(
      /hidden md:flex/,
    );
    fireEvent.click(screen.getByLabelText("Back to channels"));
    expect(push).toHaveBeenCalledWith("/app/chat");
  });
});
