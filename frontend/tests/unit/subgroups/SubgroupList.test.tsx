/**
 * @file tests/unit/subgroups/SubgroupList.test.tsx
 * @brief State rendering for SubgroupList: skeleton, error retry, empty, grid.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SubgroupList } from "@/components/subgroups/SubgroupList";
import * as hooks from "@/hooks/useSubgroups";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/hooks/useSubgroups");

const mut = { mutate: vi.fn(), isPending: false, variables: undefined };
const setList = (v: object) =>
  vi.mocked(hooks.useSubgroupList).mockReturnValue(v as never);

describe("SubgroupList", () => {
  beforeEach(() => {
    vi.mocked(hooks.useJoinSubgroup).mockReturnValue(mut as never);
    vi.mocked(hooks.useLeaveSubgroup).mockReturnValue(mut as never);
  });

  it("shows busy skeleton grid while loading", () => {
    setList({ isLoading: true });
    render(<SubgroupList onSelect={vi.fn()} />);
    expect(
      screen.getByRole("status", { name: /loading groups/i }),
    ).toBeTruthy();
  });

  it("offers retry on error", async () => {
    const refetch = vi.fn();
    setList({ isLoading: false, error: new Error("boom"), refetch });
    render(<SubgroupList onSelect={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });

  it("empty state has create CTA when onCreate given", async () => {
    const onCreate = vi.fn();
    setList({ isLoading: false, data: [] });
    render(<SubgroupList onSelect={vi.fn()} onCreate={onCreate} />);
    expect(screen.getByText(/no groups yet/i)).toBeTruthy();
    await userEvent.click(
      screen.getByRole("button", { name: /create group/i }),
    );
    expect(onCreate).toHaveBeenCalled();
  });

  it("grid is single column on mobile, 3 columns on xl", () => {
    setList({
      isLoading: false,
      data: [
        {
          id: "1",
          slug: "a",
          name: "A",
          join_policy: "open",
          description: null,
        },
      ],
    });
    const { container } = render(<SubgroupList onSelect={vi.fn()} />);
    const grid = container.querySelector("ul");
    expect(grid?.className).toMatch(/grid-cols-1/);
    expect(grid?.className).toMatch(/xl:grid-cols-3/);
  });
});
