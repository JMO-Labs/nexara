/**
 * @file tests/unit/feed/PostCard.test.tsx
 * @brief PostCard prompt badges and link preview / video embed integration.
 */
import { describe, it, expect, vi } from "vitest";
import type React from "react";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";
import { PostCard } from "@/components/feed/PostCard";
import type { Post } from "@/lib/api/posts";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/stores/session", () => ({
  useSession: vi.fn((sel) => sel({ user: { id: "u1", role: "member" } })),
}));
vi.mock("@/hooks/usePosts", () => ({
  useDeletePost: () => ({ mutate: vi.fn() }),
  useTogglePostReaction: () => ({ mutate: vi.fn() }),
}));
vi.mock("@/components/feed/CommentThread", () => ({
  CommentThread: () => null,
}));
vi.mock("@/components/feed/BookmarkButton", () => ({
  BookmarkButton: ({
    postId,
    isBookmarked,
  }: {
    postId: string;
    isBookmarked: boolean;
  }) => (
    <span data-testid="bookmark-btn" data-post={postId}>
      {String(isBookmarked)}
    </span>
  ),
}));

/** @brief Build a minimal post with optional overrides. */
function makePost(over: Partial<Post> = {}): Post {
  return {
    id: "p1",
    content: "Hello world",
    author: {
      id: "u1",
      username: "alice",
      display_name: "Alice",
      avatar_url: null,
    },
    media: [],
    poll: null,
    reactions: [],
    comment_count: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    subgroup_id: null,
    subgroup_name: null,
    subgroup_slug: null,
    ...over,
  };
}

/** @brief Render inside QueryClient + next-intl providers. */
function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <NextIntlClientProvider locale="en-US" messages={messages}>
        {ui}
      </NextIntlClientProvider>
    </QueryClientProvider>,
  );
}

describe("PostCard prompt badges", () => {
  it("shows a Prompt summary badge for summary posts", () => {
    wrap(<PostCard post={makePost({ is_prompt_summary: true })} />);
    expect(screen.getByText("Prompt summary")).toBeInTheDocument();
    expect(screen.queryByText("Reply to a prompt")).not.toBeInTheDocument();
  });

  it("shows a Reply to a prompt link for response posts", () => {
    wrap(<PostCard post={makePost({ reply_to_prompt_id: "pr-42" })} />);
    const link = screen.getByRole("link", { name: /Reply to a prompt/ });
    expect(link).toHaveAttribute("href", "/app/prompts/pr-42");
    expect(screen.queryByText("Prompt summary")).not.toBeInTheDocument();
  });

  it("shows neither badge nor label for normal posts", () => {
    wrap(<PostCard post={makePost({ reply_to_prompt_id: null })} />);
    expect(screen.queryByText("Prompt summary")).not.toBeInTheDocument();
    expect(screen.queryByText("Reply to a prompt")).not.toBeInTheDocument();
  });

  it("renders normal posts without an intl provider", () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <PostCard post={makePost()} />
      </QueryClientProvider>,
    );
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });
});

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

describe("PostCard bookmark", () => {
  it("renders BookmarkButton with post id and state", () => {
    render(<PostCard post={{ ...base, is_bookmarked: true }} />);
    const btn = screen.getByTestId("bookmark-btn");
    expect(btn).toHaveAttribute("data-post", "p1");
    expect(btn).toHaveTextContent("true");
  });
});

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
