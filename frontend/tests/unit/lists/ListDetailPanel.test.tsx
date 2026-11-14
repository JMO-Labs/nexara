/**
 * @file tests/unit/lists/ListDetailPanel.test.tsx
 * @brief ListDetailPanel: items / members / settings tabs.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { list } from "./listFixtures";

vi.mock("@/components/lists/ListGrid", () => ({
  ListGrid: ({ listId }: { listId: string }) => <p>grid {listId}</p>,
}));
vi.mock("@/components/lists/ListMemberManageModal", () => ({
  ListMemberManageModal: ({ open }: { open: boolean }) =>
    open ? <p>member modal</p> : null,
}));
vi.mock("@/components/lists/ListEditModal", () => ({
  ListEditModal: ({ open }: { open: boolean }) =>
    open ? <p>edit modal</p> : null,
}));
vi.mock("@/hooks/useListActions", () => ({
  useListMembers: () => ({
    data: [{ userId: "u9", role: "viewer", sharePersonal: false }],
    isLoading: false,
  }),
}));

import { ListDetailPanel } from "@/components/lists/ListDetailPanel";

describe("ListDetailPanel", () => {
  it("switches between items, members and settings", async () => {
    render(<ListDetailPanel list={list} communityId="c1" />);
    expect(screen.getByRole("heading", { name: "Camping gear" })).toBeVisible();
    expect(screen.getByText("grid l1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Members" }));
    expect(await screen.findByText("u9")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Manage members" }),
    );
    expect(screen.getByText("member modal")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Settings" }));
    expect(await screen.findByText("community")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Edit list" }));
    expect(screen.getByText("edit modal")).toBeInTheDocument();
  });
});
