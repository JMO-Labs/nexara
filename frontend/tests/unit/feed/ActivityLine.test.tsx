/**
 * @file tests/unit/feed/ActivityLine.test.tsx
 * @brief ActivityLine sentences, fallback and links.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ActivityLine } from "@/components/feed/ActivityLine";
import type { ActivityItem } from "@/lib/api/home";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const base: ActivityItem = {
  id: "a1",
  actor_id: "u1",
  actor_name: "Rosa",
  verb: "post.commented",
  object_type: "post",
  object_id: "p1",
  container_type: null,
  container_title: null,
  object_title: "Spring plans",
  count: 1,
  created_at: new Date().toISOString(),
};

const show = (o: Partial<ActivityItem>) =>
  render(<ActivityLine item={{ ...base, ...o }} />);

describe("ActivityLine", () => {
  it("post.commented", () => {
    show({});
    expect(
      screen.getByText("Rosa commented on Spring plans"),
    ).toBeInTheDocument();
  });
  it("post.reacted", () => {
    show({ verb: "post.reacted" });
    expect(
      screen.getByText("Rosa reacted to Spring plans"),
    ).toBeInTheDocument();
  });
  it("event.rsvp", () => {
    show({
      verb: "event.rsvp",
      object_type: "event",
      object_id: "e1",
      object_title: "Picnic",
    });
    expect(screen.getByText("Rosa is going to Picnic")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/app/events?event=e1",
    );
  });
  it("member.joined and subgroup.joined", () => {
    show({
      verb: "member.joined",
      object_type: "subgroup",
      container_title: "Book club",
    });
    expect(screen.getByText("Rosa joined Book club")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });
  it("media.uploaded singular and plural", () => {
    const { unmount } = show({ verb: "media.uploaded" });
    expect(screen.getByText("Rosa added a photo")).toBeInTheDocument();
    unmount();
    show({ verb: "media.uploaded", count: 3 });
    expect(screen.getByText("Rosa added 3 photos")).toBeInTheDocument();
  });
  it("unknown verb falls back; count appended", () => {
    show({ verb: "weird.thing", count: 2 });
    expect(screen.getByText("Rosa was active (2)")).toBeInTheDocument();
  });
  it("links post to its page and renders a time element", () => {
    const { container } = show({});
    expect(screen.getByRole("link")).toHaveAttribute("href", "/app/post/p1");
    expect(container.querySelector("time")).toHaveAttribute("datetime");
  });
});
