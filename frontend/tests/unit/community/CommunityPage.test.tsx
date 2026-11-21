/**
 * @file tests/unit/community/CommunityPage.test.tsx
 * @brief Community page: People/Groups switch bound to ?view=.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const nav = vi.hoisted(() => ({ view: null as string | null, push: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: nav.push }),
  useSearchParams: () =>
    new URLSearchParams(nav.view ? `view=${nav.view}` : ""),
}));
vi.mock("@/components/members/PeopleDirectory", () => ({
  PeopleDirectory: (p: { embedded?: boolean }) => (
    <p>{`people embedded=${p.embedded}`}</p>
  ),
}));
vi.mock("@/components/subgroups/groups-page/GroupsPage", () => ({
  GroupsPage: (p: { embedded?: boolean }) => (
    <p>{`groups embedded=${p.embedded}`}</p>
  ),
}));

import { CommunityPage } from "@/components/community/CommunityPage";

describe("CommunityPage", () => {
  beforeEach(() => {
    nav.view = null;
    nav.push.mockReset();
  });

  it("renders the header and People by default", () => {
    render(<CommunityPage />);
    expect(
      screen.getByRole("heading", { name: "Community", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText("people embedded=true")).toBeInTheDocument();
    expect(screen.queryByText("groups embedded=true")).toBeNull();
    expect(screen.getByRole("radio", { name: "People" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("renders Groups when ?view=groups", () => {
    nav.view = "groups";
    render(<CommunityPage />);
    expect(screen.getByText("groups embedded=true")).toBeInTheDocument();
    expect(screen.queryByText("people embedded=true")).toBeNull();
  });

  it("pushes ?view=groups when Groups is picked", async () => {
    render(<CommunityPage />);
    await userEvent.click(screen.getByRole("radio", { name: "Groups" }));
    expect(nav.push).toHaveBeenCalledWith("/app/community?view=groups");
  });
});
