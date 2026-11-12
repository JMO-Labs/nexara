/**
 * @file tests/unit/feed/PostCard.test.tsx
 * @brief PostCard prompt badges: summary badge and reply-to-prompt link.
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
