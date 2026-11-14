/**
 * @file tests/unit/lists/ListCard.test.tsx
 * @brief ListCard counters/owner/color, actions dropdown, delete confirm;
 *        ListCardGrid renders cards from useLists.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { list, mut } from "./listFixtures";

const h = vi.hoisted(() => ({
  del: { mutate: vi.fn(), isPending: false },
  arc: { mutate: vi.fn(), isPending: false },
  lists: vi.fn(),
}));
vi.mock("@/hooks/useLists", () => ({
  useListDelete: () => h.del,
  useListUpdate: () => mut(),
  useLists: h.lists,
}));
vi.mock("@/hooks/useListActions", () => ({ useListArchive: () => h.arc }));

import { ListCard } from "@/components/lists/ListCard";
import { ListCardGrid } from "@/components/lists/ListCardGrid";

beforeEach(() => {
  h.del.mutate.mockReset();
  h.arc.mutate.mockReset();
});

// Radix leaves body pointer-events:none briefly after menu -> dialog.
const user = userEvent.setup({ pointerEventsCheck: 0 });
const openMenu = () =>
  user.click(screen.getByRole("button", { name: "List actions" }));

describe("ListCard", () => {
  it("shows title, counters, owner and color", () => {
    render(<ListCard list={list} communityId="c1" ownerName="Ana" />);
    expect(screen.getByText("Camping gear")).toBeInTheDocument();
    expect(screen.getByText("3/10 done")).toBeInTheDocument();
    expect(screen.getByText("2 signups")).toBeInTheDocument();
    expect(screen.getByText("by Ana")).toBeInTheDocument();
    expect(screen.getByTestId("list-color")).toHaveStyle({
      backgroundColor: "#3366ff",
    });
  });

  it("delete asks for confirmation, then mutates", async () => {
    render(<ListCard list={list} communityId="c1" />);
    await openMenu();
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Delete list?");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(h.del.mutate).not.toHaveBeenCalled();
    await openMenu();
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "OK" }));
    expect(h.del.mutate).toHaveBeenCalledWith("l1", expect.anything());
  });

  it("archive and edit actions", async () => {
    render(<ListCard list={list} communityId="c1" />);
    await openMenu();
    await user.click(screen.getByRole("menuitem", { name: "Archive" }));
    expect(h.arc.mutate).toHaveBeenCalledWith("l1");
    await openMenu();
    await user.click(screen.getByRole("menuitem", { name: "Edit" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Edit list");
  });

  it("falls back without color, description, owner or onOpen", () => {
    render(
      <ListCard
        list={{ ...list, color: undefined, description: undefined }}
        communityId="c1"
      />,
    );
    expect(screen.getByTestId("list-color").getAttribute("style")).toContain(
      "var(--color-accent)",
    );
    expect(screen.queryByText("What to bring")).not.toBeInTheDocument();
    expect(screen.queryByText(/^by /)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Camping gear" }),
    ).not.toBeInTheDocument();
  });

  it("closes the delete dialog after a successful delete", async () => {
    h.del.mutate.mockImplementation(
      (_id: string, opts?: { onSuccess?: () => void }) => opts?.onSuccess?.(),
    );
    render(<ListCard list={list} communityId="c1" />);
    await openMenu();
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    await user.click(await screen.findByRole("button", { name: "OK" }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
  });

  it("opens the list on click", async () => {
    const onOpen = vi.fn();
    render(<ListCard list={list} communityId="c1" onOpen={onOpen} />);
    await user.click(screen.getByRole("button", { name: "Camping gear" }));
    expect(onOpen).toHaveBeenCalledWith(list);
  });
});

describe("ListCardGrid", () => {
  it("renders a card per list", () => {
    h.lists.mockReturnValue({ data: { lists: [list] }, isLoading: false });
    render(<ListCardGrid communityId="c1" />);
    expect(h.lists).toHaveBeenCalledWith("c1");
    expect(screen.getByText("Camping gear")).toBeInTheDocument();
  });

  it("shows skeleton and empty states", () => {
    h.lists.mockReturnValue({ data: undefined, isLoading: true });
    const { rerender } = render(<ListCardGrid communityId="c1" />);
    expect(screen.getByTestId("list-cards-loading")).toBeInTheDocument();
    h.lists.mockReturnValue({ data: { lists: [] }, isLoading: false });
    rerender(<ListCardGrid communityId="c1" />);
    expect(screen.getByText("No lists yet")).toBeInTheDocument();
  });

  it("resolves owner names and forwards onOpen", async () => {
    h.lists.mockReturnValue({ data: { lists: [list] }, isLoading: false });
    const onOpen = vi.fn();
    const ownerName = vi.fn().mockReturnValue("Ana");
    render(
      <ListCardGrid communityId="c1" onOpen={onOpen} ownerName={ownerName} />,
    );
    expect(ownerName).toHaveBeenCalledWith("u1");
    expect(screen.getByText("by Ana")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Camping gear" }));
    expect(onOpen).toHaveBeenCalledWith(list);
  });
});
