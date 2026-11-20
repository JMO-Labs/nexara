/**
 * @file tests/unit/subgroups/GroupsPage.test.tsx
 * @brief Groups index: search, All/Open/Private filter and Mine toggle.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GroupsPage } from "@/components/subgroups/groups-page/GroupsPage";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/components/subgroups/CreateSubgroupModal", () => ({
  CreateSubgroupModal: () => null,
}));

const mk = (slug: string, over: Record<string, unknown> = {}) => ({
  id: slug,
  slug,
  name: slug,
  description: `${slug} desc`,
  join_policy: "open",
  is_private: false,
  is_member: false,
  my_role: null,
  cover_media_id: null,
  accent_color: null,
  ...over,
});

const groups = [
  mk("hikers", { is_member: true }),
  mk("chess", { join_policy: "invite_only", is_private: true }),
  mk("bakers"),
];

vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({
    data: groups,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useJoinSubgroup: () => ({ mutate: vi.fn(), isPending: false }),
  useLeaveSubgroup: () => ({ mutate: vi.fn(), isPending: false }),
  useSubgroupMembers: () => ({ data: [] }),
}));

describe("GroupsPage", () => {
  it("renders heading and all groups", () => {
    render(<GroupsPage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Groups" }),
    ).toBeTruthy();
    expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(3);
  });

  it("embedded hides the header and keeps New group out of the toolbar", () => {
    render(<GroupsPage embedded />);
    expect(
      screen.queryByRole("heading", { level: 1, name: "Groups" }),
    ).toBeNull();
    const buttons = screen.getAllByRole("button", { name: "New group" });
    expect(buttons).toHaveLength(1);
    const toolbar = screen
      .getByRole("searchbox", { name: "Search groups" })
      .closest(".flex-wrap");
    expect(toolbar).not.toContainElement(buttons[0]);
  });

  it("Private filter keeps only private groups", async () => {
    render(<GroupsPage />);
    await userEvent.click(screen.getByRole("radio", { name: "Private" }));
    const names = screen
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(names).toEqual(["chess"]);
  });

  it("Open filter keeps only open-policy groups", async () => {
    render(<GroupsPage />);
    await userEvent.click(screen.getByRole("radio", { name: "Open" }));
    expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(2);
  });

  it("Mine toggle keeps only groups the viewer belongs to", async () => {
    render(<GroupsPage />);
    const mine = screen.getByRole("button", { name: "Mine" });
    expect(mine).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(mine);
    expect(mine).toHaveAttribute("aria-pressed", "true");
    const names = screen
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(names).toEqual(["hikers"]);
  });

  it("search narrows by name", async () => {
    render(<GroupsPage />);
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Search groups" }),
      "bak",
    );
    const names = screen
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(names).toEqual(["bakers"]);
  });
});
