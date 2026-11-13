/**
 * @file tests/unit/subgroups/hub/OverviewTab.test.tsx
 * @brief OverviewTab render test with empty states.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { OverviewTab } from "@/components/subgroups/hub/OverviewTab";
import type { SubgroupDetail } from "@/lib/api/subgroups";

vi.mock("@/hooks/usePosts", () => ({
  usePost: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    error: null,
  })),
  useFeed: vi.fn(() => ({
    data: { pages: [] },
    isLoading: false,
    error: null,
  })),
}));

vi.mock("@/hooks/useEvents", () => ({
  useUpcomingEvents: vi.fn(() => ({
    data: {
      items: [],
    },
    isLoading: false,
    error: null,
  })),
}));

vi.mock("@/hooks/useGalleries", () => ({
  useGalleryList: vi.fn(() => ({
    data: { items: [] },
    isLoading: false,
    error: null,
  })),
}));

const mockSubgroup: SubgroupDetail = {
  id: "sg-1",
  name: "Test Group",
  slug: "test-group",
  description: "A test subgroup",
  avatar_url: null,
  cover_media_id: null,
  is_private: false,
  join_policy: "open",
  created_by: "user-1",
  parent_id: null,
  archived_at: null,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
  member_count: 5,
  my_role: "member",
  is_member: true,
  chat_channel_id: null,
  pinned_post_id: null,
};

describe("OverviewTab", () => {
  it("renders empty states when hooks return no data", () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <OverviewTab subgroup={mockSubgroup} />
      </QueryClientProvider>,
    );
    expect(screen.getByText(/Quiet here/i)).toBeInTheDocument();
  });
});
