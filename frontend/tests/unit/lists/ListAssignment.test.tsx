/**
 * @file tests/unit/lists/ListAssignment.test.tsx
 * @brief Row assignment actions per role, and the History feed.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { item } from "./listFixtures";
import type { ItemAssignContext } from "@/hooks/useListAssignments";
import type { ListItem } from "@/lib/api/listTypes";

const h = vi.hoisted(() => ({ activity: vi.fn() }));
vi.mock("@/hooks/useMembersList", () => ({
  useMembersList: () => ({
    data: [
      { id: "u2", username: "sam", display_name: "Sam", avatar_url: null },
    ],
  }),
  matchMembers: (l: unknown[]) => l,
}));
vi.mock("@/hooks/useListAssignments", () => ({
  useListActivity: h.activity,
}));

import { ItemAssignment } from "@/components/lists/ItemAssignment";
import { ListActivityFeed } from "@/components/lists/ListActivityFeed";

const ctx = (viewerId: string, canManage: boolean): ItemAssignContext => ({
  viewerId,
  canManage,
  actions: {
    take: vi.fn(),
    assign: vi.fn(),
    accept: vi.fn(),
    decline: vi.fn(),
    release: vi.fn(),
    unassign: vi.fn(),
    busy: false,
  },
});
const withWho = (status: "pending" | "accepted"): ListItem => ({
  ...item("i1", "Chairs"),
  assignee: { id: "u1", displayName: "Maya" },
  assignmentStatus: status,
});
const btn = (name: string) => screen.queryByRole("button", { name });

describe("ItemAssignment", () => {
  it("member can take an open item but not assign", async () => {
    const c = ctx("u1", false);
    render(
      <ItemAssignment item={item("i1", "Chairs")} title="Chairs" ctx={c} />,
    );
    expect(btn("Assign Chairs")).toBeNull();
    await userEvent.click(btn("I'll take Chairs")!);
    expect(c.actions.take).toHaveBeenCalledWith("i1");
  });

  it("owner can assign via the picker", async () => {
    const c = ctx("u9", true);
    render(
      <ItemAssignment item={item("i1", "Chairs")} title="Chairs" ctx={c} />,
    );
    await userEvent.click(btn("Assign Chairs")!);
    await userEvent.click(await screen.findByRole("button", { name: /Sam/ }));
    expect(c.actions.assign).toHaveBeenCalledWith("i1", "u2");
  });

  it("pending assignee sees Accept/Decline and a Pending chip", async () => {
    const c = ctx("u1", false);
    render(<ItemAssignment item={withWho("pending")} title="Chairs" ctx={c} />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(btn("I'll take Chairs")).toBeNull();
    await userEvent.click(btn("Accept Chairs")!);
    await userEvent.click(btn("Decline Chairs")!);
    expect(c.actions.accept).toHaveBeenCalledWith("i1");
    expect(c.actions.decline).toHaveBeenCalledWith("i1");
  });

  it("accepted assignee can give back; others cannot", async () => {
    const c = ctx("u1", false);
    const { unmount } = render(
      <ItemAssignment item={withWho("accepted")} title="Chairs" ctx={c} />,
    );
    expect(screen.getByText("Accepted")).toBeInTheDocument();
    await userEvent.click(btn("Give back Chairs")!);
    expect(c.actions.release).toHaveBeenCalledWith("i1");
    unmount();
    render(
      <ItemAssignment
        item={withWho("accepted")}
        title="Chairs"
        ctx={ctx("u5", false)}
      />,
    );
    expect(btn("Give back Chairs")).toBeNull();
    expect(btn("Unassign Chairs")).toBeNull();
  });

  it("owner can unassign", async () => {
    const c = ctx("u9", true);
    render(
      <ItemAssignment item={withWho("accepted")} title="Chairs" ctx={c} />,
    );
    await userEvent.click(btn("Unassign Chairs")!);
    expect(c.actions.unassign).toHaveBeenCalledWith("i1");
  });
});

describe("ListActivityFeed", () => {
  beforeEach(() => h.activity.mockReset());
  const entry = (id: string, action: string, extra = {}) => ({
    id,
    action,
    actor: { id: "u1", displayName: "Maya" },
    itemTitle: "Folding chairs",
    createdAt: new Date(Date.now() - 2 * 3600_000).toISOString(),
    ...extra,
  });

  it("renders lines newest-first with relative time and load more", async () => {
    const fetchNextPage = vi.fn();
    h.activity.mockReturnValue({
      data: {
        pages: [
          {
            entries: [
              entry("a", "taken"),
              entry("b", "assigned", {
                targetUser: { id: "u2", displayName: "Sam" },
              }),
            ],
          },
        ],
      },
      isLoading: false,
      hasNextPage: true,
      isFetchingNextPage: false,
      fetchNextPage,
    });
    render(<ListActivityFeed listId="l1" />);
    const rows = screen.getAllByRole("listitem");
    expect(rows[0]).toHaveTextContent("Maya took Folding chairs");
    expect(rows[0]).toHaveTextContent("2h ago");
    expect(rows[1]).toHaveTextContent("Maya assigned Folding chairs to Sam");
    await userEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(fetchNextPage).toHaveBeenCalled();
  });

  it("shows an empty state", () => {
    h.activity.mockReturnValue({ data: { pages: [{ entries: [] }] } });
    render(<ListActivityFeed listId="l1" />);
    expect(screen.getByText("No activity yet")).toBeInTheDocument();
  });
});
