/**
 * @file tests/unit/components/chat/ChatLauncher.test.tsx
 * @brief ChatLauncher pill + popover/drawer with thread list.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useChatDock } from "@/stores/chatDock";
import type { ChatChannel, DmThread } from "@/lib/api/chat";

// Mock next/navigation
vi.mock("next/navigation", () => ({ usePathname: () => "/app/home" }));

// Mock the chat hooks
vi.mock("@/hooks/useChat", () => ({
  useChannels: vi.fn(),
  useDmThreads: vi.fn(),
  useChatRealtime: vi.fn(() => ({
    status: "closed",
    typing: {},
    send: vi.fn(),
    unread: {},
    markRead: vi.fn(),
  })),
}));

import { useChannels, useDmThreads } from "@/hooks/useChat";
import { ChatLauncher } from "@/components/chat/ChatLauncher";

const channels: ChatChannel[] = [
  {
    id: "c1",
    name: "general",
    channel_type: "community",
    subgroup_id: null,
    created_at: "",
  },
];
const dms: DmThread[] = [
  {
    channel_id: "d1",
    peer: {
      id: "u1",
      username: "alice",
      display_name: "Alice",
      avatar_url: null,
    },
    created_at: "",
  },
];

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
    </QueryClientProvider>,
  );
}

describe("ChatLauncher", () => {
  beforeEach(() => {
    useChatDock.setState({
      openThreadIds: [],
      minimized: {},
      launcherOpen: false,
      unreadCount: 0,
    });
    vi.mocked(useChannels).mockReturnValue({
      data: channels,
      isLoading: false,
    } as ReturnType<typeof useChannels>);
    vi.mocked(useDmThreads).mockReturnValue({
      data: dms,
      isLoading: false,
    } as ReturnType<typeof useDmThreads>);
  });

  it("renders the launcher pill button", () => {
    wrap(<ChatLauncher />);
    expect(
      screen.getByRole("button", { name: /open chat/i }),
    ).toBeInTheDocument();
  });

  it("click toggles popover open", () => {
    wrap(<ChatLauncher />);
    const btn = screen.getByRole("button", { name: /open chat/i });
    fireEvent.click(btn);
    expect(useChatDock.getState().launcherOpen).toBe(true);
  });

  it("click when open sets launcherOpen false", () => {
    useChatDock.setState({ launcherOpen: true });
    wrap(<ChatLauncher />);
    const btn = screen.getByRole("button", { name: /open chat/i });
    fireEvent.click(btn);
    expect(useChatDock.getState().launcherOpen).toBe(false);
  });

  it("lists DM threads when launcher is open", () => {
    useChatDock.setState({ launcherOpen: true });
    wrap(<ChatLauncher />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("lists channels when launcher is open", () => {
    useChatDock.setState({ launcherOpen: true });
    wrap(<ChatLauncher />);
    expect(screen.getByText(/general/)).toBeInTheDocument();
  });

  it("click a thread calls openThread and closes launcher", () => {
    useChatDock.setState({ launcherOpen: true });
    wrap(<ChatLauncher />);
    fireEvent.click(screen.getByText("Alice"));
    expect(useChatDock.getState().openThreadIds).toContain("d1");
    expect(useChatDock.getState().launcherOpen).toBe(false);
  });

  it("shows unread badge when unreadCount > 0", () => {
    useChatDock.setState({ unreadCount: 3 });
    wrap(<ChatLauncher />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
