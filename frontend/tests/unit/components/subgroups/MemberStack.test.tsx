/**
 * @file tests/unit/components/subgroups/MemberStack.test.tsx
 * @brief MemberStack renders from list-provided preview props and only falls
 *        back to the per-group members query when no preview is given.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemberStack } from "@/components/subgroups/groups-page/MemberStack";
import { useSubgroupMembers } from "@/hooks/useSubgroups";

vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupMembers: vi.fn(() => ({ data: undefined })),
}));

const preview = [1, 2, 3, 4].map((i) => ({
  id: `u${i}`,
  display_name: `Person ${i}`,
  avatar_url: null,
}));

describe("MemberStack", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders from preview props without querying members", () => {
    render(<MemberStack slug="family" preview={preview} count={7} />);
    expect(useSubgroupMembers).toHaveBeenCalledWith(null);
    expect(screen.getByText("+3")).toBeTruthy();
  });

  it("shows no overflow badge when count equals preview length", () => {
    render(<MemberStack slug="family" preview={preview} count={4} />);
    expect(screen.queryByText(/^\+\d+$/)).toBeNull();
  });

  it("renders nothing for an empty preview", () => {
    const { container } = render(
      <MemberStack slug="family" preview={[]} count={0} />,
    );
    expect(container.textContent).toBe("");
  });

  it("falls back to the members query when preview is absent", () => {
    vi.mocked(useSubgroupMembers).mockReturnValueOnce({
      data: [],
    } as unknown as ReturnType<typeof useSubgroupMembers>);
    render(<MemberStack slug="family" />);
    expect(useSubgroupMembers).toHaveBeenCalledWith("family");
  });
});
