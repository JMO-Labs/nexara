/**
 * @file tests/unit/chat/ChatHead.test.tsx
 * @brief ChatHead region, controls, send flow.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useChatDock } from "@/stores/chatDock";

vi.mock("@/hooks/useChat", () => ({
  useMessages: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
  })),
  useChatRealtime: vi.fn(() => ({ markRead: vi.fn(), unread: {} })),
  sendChatMessage: vi.fn(),
  sendChatTyping: vi.fn(),
  optimisticAddMessage: vi.fn(),
}));

import { sendChatMessage } from "@/hooks/useChat";
import { ChatHead } from "@/components/chat/ChatHead";

function wrap() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ChatHead threadId="t1" label="Alice" />
    </QueryClientProvider>,
  );
}

describe("ChatHead", () => {
  beforeEach(() =>
    useChatDock.setState({ openThreadIds: ["t1"], minimized: {} }),
  );

  it("renders labelled region", () => {
    wrap();
    expect(
      screen.getByRole("region", { name: "Conversation with Alice" }),
    ).toBeInTheDocument();
  });

  it("sends a message", () => {
    wrap();
    const ta = screen.getByPlaceholderText(/write a message/i);
    fireEvent.change(ta, { target: { value: "yo" } });
    fireEvent.click(screen.getByLabelText("Send message"));
    expect(sendChatMessage).toHaveBeenCalledWith("t1", "yo");
  });

  it("minimize and close drive the store", () => {
    wrap();
    fireEvent.click(screen.getByLabelText("Minimize"));
    expect(useChatDock.getState().minimized.t1).toBe(true);
    fireEvent.click(screen.getByLabelText("Close"));
    expect(useChatDock.getState().openThreadIds).not.toContain("t1");
  });
});
