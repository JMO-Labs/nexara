/**
 * @file tests/unit/components/chat/ThreadPane.test.tsx
 * @brief ThreadPane: density toggle, empty-state CTA focuses composer; pane layout classes.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/hooks/useActivePrompts", () => ({
  useActivePrompts: () => ({ data: [] }),
}));
import { ThreadPane } from "@/components/chat/chat-layout/ThreadPane";
import { gridClass } from "@/components/chat/chat-layout/helpers";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>
    {children}
  </QueryClientProvider>
);

const props = {
  title: "General",
  onBack: () => {},
  detailsOpen: false,
  onToggleDetails: () => {},
  typingCount: 0,
  list: {
    messages: [],
    isLoading: false,
    hasMore: false,
    isFetchingMore: false,
    onLoadMore: () => {},
  },
  composer: { onSend: () => {} },
};

describe("ThreadPane", () => {
  it("empty-state CTA focuses the composer", () => {
    render(<ThreadPane {...props} />, { wrapper });
    fireEvent.click(
      screen.getByRole("button", { name: /start conversation/i }),
    );
    expect(document.activeElement).toBe(screen.getByLabelText("Message"));
  });
  it("toggles density", () => {
    render(<ThreadPane {...props} />, { wrapper });
    const btn = screen.getByRole("button", { name: /compact density/i });
    expect(btn.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(btn);
    expect(btn.getAttribute("aria-pressed")).toBe("true");
  });
  it("keeps density across a remount (channel switch)", () => {
    window.localStorage.clear();
    const { unmount } = render(<ThreadPane {...props} />, { wrapper });
    fireEvent.click(screen.getByRole("button", { name: /compact density/i }));
    unmount();
    render(<ThreadPane {...props} />, { wrapper });
    expect(
      screen
        .getByRole("button", { name: /comfortable density/i })
        .getAttribute("aria-pressed"),
    ).toBe("true");
    window.localStorage.clear();
  });
  it("calls caller-provided CTA too", () => {
    const fn = vi.fn();
    render(
      <ThreadPane
        {...props}
        list={{ ...props.list, onStartConversation: fn }}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /start conversation/i }),
    );
    expect(fn).toHaveBeenCalled();
  });
});

describe("gridClass (pane collapse)", () => {
  it("stacks below md, 2 panes at md, inline details only at xl", () => {
    expect(gridClass(false)).toContain("grid-cols-1");
    expect(gridClass(false)).toContain("md:grid-cols-[300px_minmax(0,1fr)]");
    expect(gridClass(false)).not.toContain("_320px]");
    expect(gridClass(true)).toContain(
      "xl:grid-cols-[300px_minmax(0,1fr)_320px]",
    );
    expect(gridClass(true)).not.toContain("lg:grid-cols");
  });
});

describe("ThreadPane brand styling", () => {
  it("has no hard header divider and glass header buttons", () => {
    render(<ThreadPane {...props} />, { wrapper });
    const header = screen
      .getByRole("heading", { name: "General" })
      .closest("header") as HTMLElement;
    expect(header.className).not.toContain("border-b");
    const density = screen.getByRole("button", { name: /compact density/i });
    expect(density).toHaveClass("glass-btn", "rounded-full");
    const details = screen.getByRole("button", { name: /open details/i });
    expect(details).toHaveClass("glass-btn", "rounded-full");
  });
});
