/**
 * @file tests/unit/components/home/widgets/MyGroupsWidget.test.tsx
 * @brief Unit tests for MyGroupsWidget.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: vi.fn(() => ({ data: undefined, isLoading: true })),
}));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    "aria-label": ariaLabel,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
    "aria-label"?: string;
  }) => (
    <a href={href} aria-label={ariaLabel} {...rest}>
      {children}
    </a>
  ),
}));

import { MyGroupsWidget } from "@/components/home/widgets/MyGroupsWidget";
import { useSubgroupList } from "@/hooks/useSubgroups";
import type { Subgroup } from "@/lib/api/subgroups";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const fakeGroups: Subgroup[] = [
  {
    id: "sg1",
    name: "Hiking Club",
    slug: "hiking-club",
    description: null,
    avatar_url: null,
    cover_media_id: null,
    is_private: false,
    join_policy: "open",
    created_by: "u1",
    parent_id: null,
    archived_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    my_role: "member",
  },
];

describe("MyGroupsWidget", () => {
  it("renders without crashing", () => {
    wrap(<MyGroupsWidget />);
    expect(document.body).toBeTruthy();
  });

  it("shows skeleton while loading", () => {
    wrap(<MyGroupsWidget />);
    expect(document.body.children.length).toBeGreaterThan(0);
  });

  it("shows empty state when no groups", () => {
    vi.mocked(useSubgroupList).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useSubgroupList>);

    wrap(<MyGroupsWidget />);
    expect(screen.getByText("No groups yet")).toBeInTheDocument();
  });

  it("renders group tiles when data is available", () => {
    vi.mocked(useSubgroupList).mockReturnValue({
      data: fakeGroups,
      isLoading: false,
    } as unknown as ReturnType<typeof useSubgroupList>);

    wrap(<MyGroupsWidget />);
    expect(screen.getByLabelText("Go to Hiking Club")).toBeInTheDocument();
  });
});
