/**
 * @file tests/unit/lists/ListGrid.test.tsx
 * @brief ListGrid: infinite items, load more, skeleton, empty state.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fieldSchema, item, mut } from "./listFixtures";

const h = vi.hoisted(() => ({ items: vi.fn() }));
vi.mock("@/hooks/useLists", () => ({
  useListItems: h.items,
  useListItemComplete: () => mut(),
  useListItemCreate: () => mut(),
}));
vi.mock("@/hooks/useListActions", () => ({
  useListItemDelete: () => mut(),
  useListItemUpdate: () => mut(),
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

beforeEach(() => h.items.mockReset());

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
});
