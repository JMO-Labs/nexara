/**
 * @file tests/unit/components/feed/PostCard.SourceBadge.test.tsx
 * @brief Verifies SourceBadge renders within PostCard.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PostCard } from "@/components/feed/PostCard";
import type { Post } from "@/lib/api/posts";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    onClick,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
    onClick?: (e: React.MouseEvent) => void;
    [key: string]: unknown;
  }) => (
    <a href={href} onClick={onClick} {...rest}>
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

const fakePost: Post = {
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
  subgroup_id: "sg-1",
  subgroup_name: "Hiking Club",
  subgroup_slug: "hiking-club",
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("PostCard SourceBadge integration", () => {
  it("renders SourceBadge with subgroup name", () => {
    wrap(<PostCard post={fakePost} />);
    expect(screen.getByText("Hiking Club")).toBeInTheDocument();
  });

  it("renders Community pill when subgroup_id is null", () => {
    const communityPost: Post = {
      ...fakePost,
      subgroup_id: null,
      subgroup_name: null,
    };
    wrap(<PostCard post={communityPost} />);
    expect(screen.getByText("Community")).toBeInTheDocument();
  });
});

describe("PostCard polish", () => {
  it("uses 12px mobile / 16px desktop padding and a hover shade", () => {
    const { container } = wrap(<PostCard post={fakePost} />);
    const cls = (container.firstElementChild as HTMLElement).className;
    expect(cls).toContain("p-3");
    expect(cls).toContain("md:p-4");
    expect(cls).not.toMatch(/(^|\s)p-4/);
    expect(cls).toContain("transition-colors");
    expect(cls).toContain("hover:bg-");
  });
});
