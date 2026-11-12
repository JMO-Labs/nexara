/**
 * @file tests/unit/components/chat/ThreadPane.test.tsx
 * @brief ThreadPane: density toggle, empty-state CTA focuses composer; pane layout classes.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  ThreadPane,
  DetailsPane,
} from "@/components/chat/chat-layout/ThreadPane";
import { gridClass } from "@/components/chat/chat-layout/helpers";

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
    render(<ThreadPane {...props} />);
    fireEvent.click(
      screen.getByRole("button", { name: /start conversation/i }),
    );
    expect(document.activeElement).toBe(screen.getByLabelText("Message"));
  });
  it("toggles density", () => {
    render(<ThreadPane {...props} />);
    const btn = screen.getByRole("button", { name: /compact density/i });
    expect(btn.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(btn);
    expect(btn.getAttribute("aria-pressed")).toBe("true");
  });
  it("keeps density across a remount (channel switch)", () => {
    window.localStorage.clear();
    const { unmount } = render(<ThreadPane {...props} />);
    fireEvent.click(screen.getByRole("button", { name: /compact density/i }));
    unmount();
    render(<ThreadPane {...props} />);
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
  it("stacks below md, 2 panes at md, 3 panes only at lg", () => {
    expect(gridClass(false)).toContain("grid-cols-1");
    expect(gridClass(false)).toContain("md:grid-cols-[280px_1fr]");
    expect(gridClass(false)).not.toContain("_320px]");
    expect(gridClass(true)).toContain("md:grid-cols-[280px_1fr]");
    expect(gridClass(true)).not.toContain("md:grid-cols-[280px_1fr_320px]");
    expect(gridClass(true)).toContain("lg:grid-cols-[280px_1fr_320px]");
  });
  it("details pane shows only at lg", () => {
    render(<DetailsPane />);
    const aside = screen.getByRole("complementary", { name: "Details" });
    expect(aside.className).toContain("lg:flex");
    expect(aside.className).not.toContain("md:flex");
  });
});
