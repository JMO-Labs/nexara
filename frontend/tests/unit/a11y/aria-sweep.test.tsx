/**
 * @file tests/unit/a11y/aria-sweep.test.tsx
 * @brief ARIA labels on feed/event cards, palette live region, Lightbox isolation.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PostCard } from "@/components/feed/PostCard";
import { EventCard } from "@/components/events/EventCard";
import { axe } from "vitest-axe";
import * as axeMatchers from "vitest-axe/matchers";
import { AvatarMenu } from "@/components/layout/AvatarMenu";
import { GlobalCommandPalette } from "@/components/search/GlobalCommandPalette";
import { useUI } from "@/stores/ui";
import { Lightbox } from "@/components/galleries/Lightbox";
import type { Post } from "@/lib/api/posts";
import type { EventItem } from "@/lib/api/events";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
vi.mock("@/hooks/useSearch", () => ({
  useGlobalSearch: () => ({
    data: { items: [], next_cursor: null, has_more: false },
    isLoading: false,
  }),
}));
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver;
Element.prototype.scrollIntoView ??= () => {};
expect.extend(axeMatchers);
declare module "vitest" {
  interface Assertion {
    toHaveNoViolations(): void;
  }
}
vi.mock("@/stores/session", () => ({
  useSession: vi.fn((sel) => sel({ user: { id: "u1", role: "member" } })),
}));
vi.mock("@/hooks/usePosts", () => ({
  useDeletePost: () => ({ mutate: vi.fn() }),
  useTogglePostReaction: () => ({ mutate: vi.fn() }),
}));

const mkPost = (content: string) =>
  ({
    id: "p1",
    content,
    author: {
      id: "u1",
      username: "a",
      display_name: "Alice",
      avatar_url: null,
    },
    media: [],
    poll: null,
    reactions: [{ emoji: "👍", count: 2, reacted_by_me: false }],
    comment_count: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    subgroup_id: null,
    subgroup_name: null,
    subgroup_slug: null,
  }) as Post;
const mkEvent = () =>
  ({
    id: "e1",
    title: "Picnic",
    description: null,
    location: "Park",
    starts_at: "2026-05-01T18:00:00Z",
    ends_at: "2026-05-01T20:00:00Z",
    is_all_day: false,
    rsvp_labels: { attending: "Going" },
    rsvp_counts: {},
    contribution_slots: [],
    user_rsvp: null,
  }) as unknown as EventItem;

const qc = () => new QueryClient();
const wrap = (ui: React.ReactNode) =>
  render(<QueryClientProvider client={qc()}>{ui}</QueryClientProvider>);

describe("aria sweep", () => {
  it("PostCard has descriptive aria-label", () => {
    const post = {
      id: "p1",
      content: "Hello world\nsecond line",
      author: {
        id: "u1",
        username: "a",
        display_name: "Alice",
        avatar_url: null,
      },
      media: [],
      poll: null,
      reactions: [{ emoji: "👍", count: 2, reacted_by_me: false }],
      comment_count: 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      subgroup_id: null,
      subgroup_name: null,
      subgroup_slug: null,
    } as Post;
    wrap(<PostCard post={post} />);
    expect(
      screen.getByLabelText(
        "Post by Alice: Hello world. 2 reactions, 3 comments.",
      ),
    ).toBeTruthy();
  });

  it("EventCard has descriptive aria-label", () => {
    const ev = {
      id: "e1",
      title: "Picnic",
      description: null,
      location: "Park",
      starts_at: "2026-05-01T18:00:00Z",
      ends_at: "2026-05-01T20:00:00Z",
      is_all_day: false,
      rsvp_labels: { attending: "Going" },
      rsvp_counts: {},
      contribution_slots: [],
      user_rsvp: null,
    } as unknown as EventItem;
    wrap(<EventCard event={ev} />);
    expect(screen.getByLabelText(/^Event: Picnic\./)).toBeTruthy();
  });

  it("Lightbox Close click does not bubble to a parent", () => {
    const parent = vi.fn();
    const onClose = vi.fn();
    const items = [
      {
        id: "i",
        gallery_id: "g",
        media_id: "m",
        added_by: "u",
        caption: "c",
        position: 0,
        created_at: "",
      },
    ];
    render(
      <div onClick={parent}>
        <Lightbox
          items={items}
          index={0}
          onClose={onClose}
          onIndexChange={() => {}}
        />
      </div>,
    );
    fireEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(parent).not.toHaveBeenCalled();
  });

  it("PostCard omits the headline part for media-only posts", () => {
    wrap(<PostCard post={mkPost("")} />);
    expect(
      screen.getByLabelText("Post by Alice. 2 reactions, 3 comments."),
    ).toBeTruthy();
  });

  it("AvatarMenu trigger declares aria-haspopup=menu", () => {
    render(<AvatarMenu />);
    expect(screen.getByLabelText("Account menu")).toHaveAttribute(
      "aria-haspopup",
      "menu",
    );
  });

  it("GlobalCommandPalette list is a polite live region", async () => {
    wrap(<GlobalCommandPalette />);
    act(() => useUI.getState().setCommandPaletteOpen(true));
    const list = await screen.findByRole("listbox");
    expect(list).toHaveAttribute("aria-live", "polite");
  });

  describe("axe", () => {
    it("PostCard has no violations", async () => {
      const { container } = wrap(<PostCard post={mkPost("Hello")} />);
      expect(await axe(container)).toHaveNoViolations();
    });
    it("EventCard has no violations", async () => {
      const { container } = wrap(<EventCard event={mkEvent()} />);
      expect(await axe(container)).toHaveNoViolations();
    });
    it("AvatarMenu has no violations", async () => {
      const { container } = render(<AvatarMenu />);
      expect(await axe(container)).toHaveNoViolations();
    });
    it("GlobalCommandPalette has no violations", async () => {
      wrap(<GlobalCommandPalette />);
      act(() => useUI.getState().setCommandPaletteOpen(true));
      await screen.findByRole("listbox");
      expect(await axe(document.body)).toHaveNoViolations();
    });
  });
});
