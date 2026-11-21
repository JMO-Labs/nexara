/**
 * @file tests/unit/subgroups/hub/ListsTab.test.tsx
 * @brief Group hub Lists tab: New list link and subgroup-scoped grid.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/hooks/useCommunityId", () => ({ useCommunityId: () => "c1" }));
vi.mock("@/components/lists/ListCardGrid", () => ({
  ListCardGrid: (p: {
    communityId: string;
    subgroupId?: string;
    onOpen: (l: { id: string }) => void;
  }) => (
    <button onClick={() => p.onOpen({ id: "l1" })}>
      grid {p.communityId} {p.subgroupId}
    </button>
  ),
}));

import { ListsTab } from "@/components/subgroups/hub/ListsTab";

describe("ListsTab", () => {
  it("links New list to the group and scopes the grid to it", async () => {
    render(<ListsTab subgroup={{ id: "s1" } as never} />);
    expect(screen.getByRole("link", { name: /New list/ })).toHaveAttribute(
      "href",
      "/app/lists/new?subgroup=s1",
    );
    expect(screen.getByText("grid c1 s1")).toBeInTheDocument();
    await userEvent.click(screen.getByText("grid c1 s1"));
    expect(push).toHaveBeenCalledWith("/app/lists/l1");
  });
});
