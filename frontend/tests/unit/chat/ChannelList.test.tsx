/**
 * @file tests/unit/chat/ChannelList.test.tsx
 * @brief Renders channels + DMs, highlights active, fires onSelect.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { ChannelList } from "@/components/chat/ChannelList";
import type { ChatChannel, DmThread } from "@/lib/api/chat";

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
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
});
