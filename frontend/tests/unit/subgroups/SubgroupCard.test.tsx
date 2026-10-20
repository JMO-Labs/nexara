/**
 * @file tests/unit/subgroups/SubgroupCard.test.tsx
 * @brief Renders subgroup card; join/leave/select callbacks fire correctly.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { useRouter } from "next/navigation";
import { SubgroupCard } from "@/components/subgroups/SubgroupCard";
import type { Subgroup } from "@/lib/api/subgroups";

vi.mock("next/navigation");

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

const sg: Subgroup = {
  id: "sg1",
  name: "Hiking",
  slug: "hiking",
  description: "Trails",
  avatar_url: null,
  cover_media_id: null,
  is_private: false,
  join_policy: "open",
  created_by: null,
  parent_id: null,
  archived_at: null,
  created_at: "2026-04-25T00:00:00Z",
  updated_at: "2026-04-25T00:00:00Z",
  my_role: null,
};

describe("SubgroupCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders name + description + member count", () => {
    wrap(<SubgroupCard subgroup={sg} memberCount={4} onSelect={() => {}} />);
    expect(screen.getByText("Hiking")).toBeInTheDocument();
    expect(screen.getByText("Trails")).toBeInTheDocument();
    expect(screen.getByText(/4 members/)).toBeInTheDocument();
  });

  it("fires onJoin when not a member (open join_policy)", () => {
    const onJoin = vi.fn();
    wrap(<SubgroupCard subgroup={sg} onSelect={() => {}} onJoin={onJoin} />);
    fireEvent.click(screen.getByRole("button", { name: "Join" }));
    expect(onJoin).toHaveBeenCalledWith("hiking");
  });

  it("fires onLeave when member", () => {
    const onLeave = vi.fn();
    wrap(
      <SubgroupCard
        subgroup={sg}
        isMember
        onSelect={() => {}}
        onLeave={onLeave}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Leave" }));
    expect(onLeave).toHaveBeenCalledWith("hiking");
  });

  it('renders "Invite required" disabled button when invite_only + not member', () => {
    const sg_invite = { ...sg, join_policy: "invite_only" as const };
    wrap(<SubgroupCard subgroup={sg_invite} onSelect={() => {}} />);
    const btn = screen.getByRole("button", { name: "Invite required" });
    expect(btn).toBeDisabled();
  });

  it('renders "Request to join" button when admin_approval + not member', () => {
    const sg_approval = { ...sg, join_policy: "admin_approval" as const };
    const onJoin = vi.fn();
    wrap(
      <SubgroupCard
        subgroup={sg_approval}
        onSelect={() => {}}
        onJoin={onJoin}
      />,
    );
    const btn = screen.getByRole("button", { name: "Request to join" });
    fireEvent.click(btn);
    expect(onJoin).toHaveBeenCalledWith("hiking");
  });

  it('navigates to hub route when "Open →" button clicked', () => {
    const mockPush = vi.fn();
    vi.mocked(useRouter).mockReturnValue({ push: mockPush } as any);
    const onSelect = vi.fn();
    wrap(<SubgroupCard subgroup={sg} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: "Open →" }));
    expect(mockPush).toHaveBeenCalledWith("/app/subgroups/hiking");
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("card body click still calls onSelect", () => {
    const mockPush = vi.fn();
    vi.mocked(useRouter).mockReturnValue({ push: mockPush } as any);
    const onSelect = vi.fn();
    const { container } = render(
      <CssVarsProvider theme={joyTheme}>
        <SubgroupCard subgroup={sg} onSelect={onSelect} />
      </CssVarsProvider>,
    );
    const card = container.querySelector('[role="button"]');
    if (card) {
      fireEvent.click(card);
    }
    expect(onSelect).toHaveBeenCalledWith("hiking");
  });
});
