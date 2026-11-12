/**
 * @file tests/unit/components/subgroups/GroupMosaic.test.tsx
 * @brief State rendering for GroupMosaic: skeleton, error retry, empty CTA, grid.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GroupMosaic } from "@/components/subgroups/groups-page/GroupMosaic";
import type { GroupMosaicProps } from "@/components/subgroups/groups-page/GroupMosaic";

const base: GroupMosaicProps = {
  data: [],
  isLoading: false,
  error: null,
  onSelect: vi.fn(),
  onJoin: vi.fn(),
  onLeave: vi.fn(),
  joinBusy: null,
  leaveBusy: null,
  onCreate: vi.fn(),
};

describe("GroupMosaic", () => {
  it("shows busy skeleton grid while loading", () => {
    render(<GroupMosaic {...base} isLoading />);
    const el = screen.getByRole("status", { name: /loading groups/i });
    expect(el.getAttribute("aria-busy")).toBe("true");
  });

  it("retry calls onRetry", async () => {
    const onRetry = vi.fn();
    render(
      <GroupMosaic {...base} error={new Error("boom")} onRetry={onRetry} />,
    );
    expect(screen.getByText("boom")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("empty community shows Create group CTA", async () => {
    const onCreate = vi.fn();
    render(<GroupMosaic {...base} onCreate={onCreate} />);
    expect(screen.getByText(/no groups yet/i)).toBeTruthy();
    await userEvent.click(
      screen.getByRole("button", { name: /create group/i }),
    );
    expect(onCreate).toHaveBeenCalled();
  });

  it("filtered-out list shows no-match message", () => {
    render(<GroupMosaic {...base} isFiltered />);
    expect(screen.getByText(/no groups match/i)).toBeTruthy();
  });

  it("grid is single column on mobile and 3 columns on lg", () => {
    const g = {
      id: "1",
      slug: "a",
      name: "A",
      join_policy: "open",
      description: null,
    };
    const { container } = render(<GroupMosaic {...base} data={[g as never]} />);
    const grid = container.firstElementChild;
    expect(grid?.className).toMatch(/grid-cols-1/);
    expect(grid?.className).toMatch(/lg:grid-cols-3/);
  });
});
