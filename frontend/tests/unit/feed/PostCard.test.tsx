/**
 * @file tests/unit/feed/PostCard.test.tsx
 * @brief PostCard link preview / video embed integration.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PostCard } from "@/components/feed/PostCard";
import type { Post } from "@/lib/api/posts";

vi.mock("@/hooks/usePosts", () => ({
  useTogglePostReaction: () => ({ mutate: vi.fn() }),
  useDeletePost: () => ({ mutate: vi.fn() }),
}));
vi.mock("@/components/feed/CommentThread", () => ({
  CommentThread: () => null,
}));

const base = {
  id: "p1",
  content: "hello",
  author: { id: "u1", username: "a", display_name: "Alice", avatar_url: null },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  reactions: [],
  comment_count: 0,
  media: [],
} as unknown as Post;

const link = {
  id: "l1",
  url: "https://example.com/x",
  og_title: "Example title",
  og_description: "desc",
  og_image: null,
  og_site_name: "Example",
  provider_type: null,
  provider_id: null,
};
const video = {
  ...link,
  id: "v1",
  url: "https://youtu.be/abc123",
  og_title: "Video title",
  provider_type: "youtube",
  provider_id: "abc123",
};

describe("PostCard link previews", () => {
  it("renders no wrapper without previews", () => {
    const { container } = render(<PostCard post={base} />);
    expect(container.querySelector("[data-testid=post-previews]")).toBeNull();
  });

  it("renders LinkPreviewCard for non-video and VideoEmbed for video", () => {
    render(<PostCard post={{ ...base, link_previews: [link, video] }} />);
    expect(screen.getByTestId("link-preview-title")).toHaveTextContent(
      "Example title",
    );
    expect(
      screen.getByRole("button", { name: /Video: youtube/ }),
    ).toBeInTheDocument();
  });

  it("wraps previews with mt-3 space-y-2 and min-w-0 for mobile", () => {
    render(<PostCard post={{ ...base, link_previews: [link] }} />);
    const wrap = screen.getByTestId("post-previews");
    expect(wrap).toHaveClass("mt-3", "space-y-2", "min-w-0", "max-w-full");
  });

  it("places previews after body and before media", () => {
    const media = [{ id: "m1", url: "/m.jpg", mime_type: "image/jpeg" }];
    render(
      <PostCard
        post={{ ...base, media, link_previews: [link] } as unknown as Post}
      />,
    );
    const wrap = screen.getByTestId("post-previews");
    const body = screen.getByText("hello");
    expect(
      body.compareDocumentPosition(wrap) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    const img = document.querySelector("img[src*='m.jpg']");
    expect(img).not.toBeNull();
    expect(
      wrap.compareDocumentPosition(img!) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("falls back to card when video id is unsafe", () => {
    const bad = { ...video, provider_id: "../x" };
    render(<PostCard post={{ ...base, link_previews: [bad] }} />);
    expect(screen.getByTestId("link-preview-title")).toBeInTheDocument();
  });
});
