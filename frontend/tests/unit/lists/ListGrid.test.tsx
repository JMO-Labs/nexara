/**
 * @file tests/unit/lists/ListGrid.test.tsx
 * @brief ListGrid: infinite items, load more, skeleton, empty state and
 *        row actions (toggle, edit, delete with confirmation).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fieldSchema, item, mut } from "./listFixtures";

const h = vi.hoisted(() => ({
  items: vi.fn(),
  complete: { mutate: vi.fn(), isPending: false },
  remove: { mutate: vi.fn(), isPending: false },
  confirm: vi.fn(),
}));
vi.mock("@/hooks/useLists", () => ({
  useListItems: h.items,
  useListItemComplete: () => h.complete,
  useListItemCreate: () => mut(),
}));
vi.mock("@/hooks/useListActions", () => ({
  useListItemDelete: () => h.remove,
  useListItemUpdate: () => mut(),
}));
vi.mock("@/stores/confirmDialog", () => ({
  useConfirmDialog: (sel: (s: unknown) => unknown) =>
    sel({ confirm: h.confirm }),
}));

import { ListGrid } from "@/components/lists/ListGrid";

const q = (over: Record<string, unknown>) => ({
  data: undefined,
  isLoading: false,
  hasNextPage: false,
  isFetchingNextPage: false,
  fetchNextPage: vi.fn(),
  ...over,
});

beforeEach(() => {
  h.items.mockReset();
  h.complete.mutate.mockReset();
  h.remove.mutate.mockReset();
  h.confirm.mockReset();
});

const withItems = () =>
  h.items.mockReturnValue(
    q({ data: { pages: [{ items: [item("a", "Tent")] }] } }),
  );

describe("ListGrid", () => {
  it("renders items across pages and loads more", async () => {
    const r = q({
      data: {
        pages: [
          { items: [item("a", "Tent")] },
          { items: [item("b", "Stove")] },
        ],
      },
      hasNextPage: true,
    });
    h.items.mockReturnValue(r);
    render(<ListGrid listId="l1" fieldSchema={fieldSchema} />);
    expect(h.items).toHaveBeenCalledWith("l1");
    expect(screen.getByText("Tent")).toBeInTheDocument();
    expect(screen.getByText("Stove")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(r.fetchNextPage).toHaveBeenCalled();
  });

  it("disables load more without next page and while fetching", () => {
    h.items.mockReturnValue(
      q({
        data: { pages: [{ items: [item("a", "Tent")] }] },
        isFetchingNextPage: true,
      }),
    );
    render(<ListGrid listId="l1" fieldSchema={fieldSchema} />);
    const btn = screen.getByRole("button", { name: /Load more/ });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-busy", "true");
  });

  it("shows skeletons while loading", () => {
    h.items.mockReturnValue(q({ isLoading: true }));
    render(<ListGrid listId="l1" fieldSchema={fieldSchema} />);
    expect(screen.getByTestId("list-grid-loading")).toBeInTheDocument();
  });

  it("empty state opens the item create modal", async () => {
    h.items.mockReturnValue(q({ data: { pages: [{ items: [] }] } }));
    render(<ListGrid listId="l1" fieldSchema={fieldSchema} />);
    expect(screen.getByText("No items yet, create one")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Add item" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("New item");
  });

  it("toggling a row completes the item", async () => {
    withItems();
    render(<ListGrid listId="l1" fieldSchema={fieldSchema} />);
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Complete Tent" }),
    );
    expect(h.complete.mutate).toHaveBeenCalledWith({
      itemId: "a",
      completed: true,
    });
  });

  it("edit opens the item modal", async () => {
    withItems();
    render(<ListGrid listId="l1" fieldSchema={fieldSchema} />);
    await userEvent.click(screen.getByRole("button", { name: "Edit Tent" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Edit item");
  });

  it("new item button opens the create modal", async () => {
    withItems();
    render(<ListGrid listId="l1" fieldSchema={fieldSchema} />);
    await userEvent.click(screen.getByRole("button", { name: "New item" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("New item");
  });

  it("delete confirms before removing", async () => {
    withItems();
    h.confirm.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(<ListGrid listId="l1" fieldSchema={fieldSchema} />);
    const del = screen.getByRole("button", { name: "Delete Tent" });
    await userEvent.click(del);
    expect(h.confirm).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Delete item?", tone: "danger" }),
    );
    expect(h.remove.mutate).not.toHaveBeenCalled();
    await userEvent.click(del);
    await waitFor(() => expect(h.remove.mutate).toHaveBeenCalledWith("a"));
  });
});
