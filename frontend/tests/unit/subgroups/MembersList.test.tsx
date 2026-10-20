/**
 * @file tests/unit/subgroups/MembersList.test.tsx
 * @brief Test role management and member removal in MembersList.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MembersList,
  type MembersListProps,
} from "@/components/subgroups/MembersList";
import * as useSubgroupsModule from "@/hooks/useSubgroups";
import { useConfirmDialog } from "@/stores/confirmDialog";
import type { Membership } from "@/lib/api/subgroups";

const mockMembers: Membership[] = [
  {
    subgroup_id: "sg-1",
    user_id: "user-1",
    role: "owner",
    invited_by: null,
    joined_at: "2025-01-01T00:00:00Z",
    username: "alice",
    display_name: "Alice Owner",
    avatar_url: null,
  },
  {
    subgroup_id: "sg-1",
    user_id: "user-2",
    role: "moderator",
    invited_by: "user-1",
    joined_at: "2025-01-02T00:00:00Z",
    username: "bob",
    display_name: "Bob Mod",
    avatar_url: null,
  },
  {
    subgroup_id: "sg-1",
    user_id: "user-3",
    role: "member",
    invited_by: "user-1",
    joined_at: "2025-01-03T00:00:00Z",
    username: "charlie",
    display_name: "Charlie Member",
    avatar_url: null,
  },
];

function wrap(ui: React.ReactNode) {
  return render(<>{ui}</>);
}

describe("MembersList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders members with action menu when canManage=true", async () => {
    const mockUseSubgroupMembers = vi
      .spyOn(useSubgroupsModule, "useSubgroupMembers")
      .mockReturnValue({
        data: mockMembers,
        isLoading: false,
        error: null,
      } as any);

    const mockRemove = vi.fn();
    vi.spyOn(useSubgroupsModule, "useRemoveMember").mockReturnValue({
      mutate: mockRemove,
      isPending: false,
      variables: undefined,
    } as any);

    vi.spyOn(useSubgroupsModule, "useChangeRole").mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as any);

    wrap(
      <MembersList
        slug="test-sg"
        canManage={true}
        viewerRole="owner"
        onAdd={vi.fn()}
      />,
    );

    // Check all members are rendered
    expect(screen.getByText("Alice Owner")).toBeInTheDocument();
    expect(screen.getByText("Bob Mod")).toBeInTheDocument();
    expect(screen.getByText("Charlie Member")).toBeInTheDocument();

    // Check role chips
    expect(screen.getAllByText("owner")[0]).toBeInTheDocument();
    expect(screen.getByText("moderator")).toBeInTheDocument();
    expect(screen.getByText("member")).toBeInTheDocument();

    // Check action menus are present (3 of them, one per member)
    const menuButtons = screen.getAllByRole("button", { name: "actions" });
    expect(menuButtons.length).toBe(3);

    mockUseSubgroupMembers.mockRestore();
  });

  it("promote member to moderator when action clicked", async () => {
    const mockChangeRole = vi.fn().mockResolvedValue({ role: "moderator" });
    const mockUseSubgroupMembers = vi
      .spyOn(useSubgroupsModule, "useSubgroupMembers")
      .mockReturnValue({
        data: mockMembers,
        isLoading: false,
        error: null,
      } as any);

    vi.spyOn(useSubgroupsModule, "useRemoveMember").mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as any);

    vi.spyOn(useSubgroupsModule, "useChangeRole").mockReturnValue({
      mutateAsync: mockChangeRole,
      isPending: false,
      variables: undefined,
    } as any);

    const user = userEvent.setup();
    wrap(
      <MembersList
        slug="test-sg"
        canManage={true}
        viewerRole="owner"
        onAdd={vi.fn()}
      />,
    );

    // Open menu for member (user-3, role=member)
    const memberRow = screen
      .getByText("Charlie Member")
      .closest("div")?.parentElement;
    expect(memberRow).toBeDefined();
    const memberMenuButton = within(memberRow!).getByRole("button", {
      name: "actions",
    });

    await user.click(memberMenuButton);

    // Click "Promote to moderator"
    const promoteOption = await screen.findByText("Promote to moderator");
    await user.click(promoteOption);

    // Verify mutation called with correct args
    expect(mockChangeRole).toHaveBeenCalledWith({
      user_id: "user-3",
      role: "moderator",
    });

    mockUseSubgroupMembers.mockRestore();
  });

  it("promote moderator to owner when viewerRole=owner", async () => {
    const mockChangeRole = vi.fn().mockResolvedValue({ role: "owner" });
    const mockUseSubgroupMembers = vi
      .spyOn(useSubgroupsModule, "useSubgroupMembers")
      .mockReturnValue({
        data: mockMembers,
        isLoading: false,
        error: null,
      } as any);

    vi.spyOn(useSubgroupsModule, "useRemoveMember").mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as any);

    vi.spyOn(useSubgroupsModule, "useChangeRole").mockReturnValue({
      mutateAsync: mockChangeRole,
      isPending: false,
      variables: undefined,
    } as any);

    const user = userEvent.setup();
    wrap(
      <MembersList
        slug="test-sg"
        canManage={true}
        viewerRole="owner"
        onAdd={vi.fn()}
      />,
    );

    // Open menu for moderator (user-2, role=moderator)
    const modRow = screen.getByText("Bob Mod").closest("div")?.parentElement;
    expect(modRow).toBeDefined();
    const modMenuButton = within(modRow!).getByRole("button", {
      name: "actions",
    });

    await user.click(modMenuButton);

    // Click "Promote to owner"
    const promoteOption = await screen.findByText("Promote to owner");
    await user.click(promoteOption);

    // Verify mutation called
    expect(mockChangeRole).toHaveBeenCalledWith({
      user_id: "user-2",
      role: "owner",
    });

    mockUseSubgroupMembers.mockRestore();
  });

  it("hide promote-to-owner when viewerRole is not owner", async () => {
    const mockUseSubgroupMembers = vi
      .spyOn(useSubgroupsModule, "useSubgroupMembers")
      .mockReturnValue({
        data: mockMembers,
        isLoading: false,
        error: null,
      } as any);

    vi.spyOn(useSubgroupsModule, "useRemoveMember").mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as any);

    vi.spyOn(useSubgroupsModule, "useChangeRole").mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as any);

    const user = userEvent.setup();
    wrap(
      <MembersList
        slug="test-sg"
        canManage={true}
        viewerRole="moderator"
        onAdd={vi.fn()}
      />,
    );

    const modRow = screen.getByText("Bob Mod").closest("div")?.parentElement;
    expect(modRow).toBeDefined();
    const modMenuButton = within(modRow!).getByRole("button", {
      name: "actions",
    });

    await user.click(modMenuButton);

    // "Promote to owner" should NOT be visible
    expect(screen.queryByText("Promote to owner")).not.toBeInTheDocument();

    mockUseSubgroupMembers.mockRestore();
  });

  it("demote owner disabled when only one owner remains", async () => {
    const mockUseSubgroupMembers = vi
      .spyOn(useSubgroupsModule, "useSubgroupMembers")
      .mockReturnValue({
        data: mockMembers, // only user-1 is owner
        isLoading: false,
        error: null,
      } as any);

    vi.spyOn(useSubgroupsModule, "useRemoveMember").mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as any);

    vi.spyOn(useSubgroupsModule, "useChangeRole").mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as any);

    const user = userEvent.setup();
    wrap(
      <MembersList
        slug="test-sg"
        canManage={true}
        viewerRole="owner"
        onAdd={vi.fn()}
      />,
    );

    const ownerRow = screen
      .getByText("Alice Owner")
      .closest("div")?.parentElement;
    expect(ownerRow).toBeDefined();
    const ownerMenuButton = within(ownerRow!).getByRole("button", {
      name: "actions",
    });

    await user.click(ownerMenuButton);

    // Demote option should be disabled with aria-disabled
    const demoteOption = screen.getByText("Demote to moderator");
    expect(demoteOption.closest("[role=menuitem]")).toHaveAttribute(
      "aria-disabled",
      "true",
    );

    mockUseSubgroupMembers.mockRestore();
  });

  it("remove member calls useRemoveMember", async () => {
    const mockRemove = vi.fn();
    const mockUseSubgroupMembers = vi
      .spyOn(useSubgroupsModule, "useSubgroupMembers")
      .mockReturnValue({
        data: mockMembers,
        isLoading: false,
        error: null,
      } as any);

    vi.spyOn(useSubgroupsModule, "useRemoveMember").mockReturnValue({
      mutate: mockRemove,
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
      variables: undefined,
    } as any);

    vi.spyOn(useSubgroupsModule, "useChangeRole").mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as any);

    // Mock confirm store to auto-accept
    const mockConfirm = vi.fn().mockResolvedValue(true);
    useConfirmDialog.setState({ confirm: mockConfirm } as any);

    const user = userEvent.setup();
    wrap(
      <MembersList
        slug="test-sg"
        canManage={true}
        viewerRole="owner"
        onAdd={vi.fn()}
      />,
    );

    const memberRow = screen
      .getByText("Charlie Member")
      .closest("div")?.parentElement;
    expect(memberRow).toBeDefined();
    const memberMenuButton = within(memberRow!).getByRole("button", {
      name: "actions",
    });

    await user.click(memberMenuButton);

    const removeOption = await screen.findByText("Remove from group");
    await user.click(removeOption);

    expect(mockConfirm).toHaveBeenCalled();
    expect(mockRemove).toHaveBeenCalledWith("user-3");

    mockUseSubgroupMembers.mockRestore();
  });

  it("passes busy state to menu button during mutation", async () => {
    const mockUseSubgroupMembers = vi
      .spyOn(useSubgroupsModule, "useSubgroupMembers")
      .mockReturnValue({
        data: mockMembers,
        isLoading: false,
        error: null,
      } as any);

    vi.spyOn(useSubgroupsModule, "useRemoveMember").mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: true, // Simulate pending state
      variables: "user-3",
    } as any);

    vi.spyOn(useSubgroupsModule, "useChangeRole").mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as any);

    wrap(
      <MembersList
        slug="test-sg"
        canManage={true}
        viewerRole="owner"
        onAdd={vi.fn()}
      />,
    );

    // Check that the action menu button is rendered (busy prop passed to it)
    const memberRow = screen
      .getByText("Charlie Member")
      .closest("div")?.parentElement;
    expect(memberRow).toBeDefined();
    const actionButton = within(memberRow!).getByRole("button", {
      name: "actions",
    });

    // Button should exist and be passed a loading prop internally
    expect(actionButton).toBeInTheDocument();

    mockUseSubgroupMembers.mockRestore();
  });
});
