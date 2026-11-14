/**
 * @file tests/unit/lists/ListModals.test.tsx
 * @brief Create/edit list modals: validation, submit, cancel.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { list } from "./listFixtures";

const h = vi.hoisted(() => ({
  create: { mutate: vi.fn(), isPending: false },
  update: { mutate: vi.fn(), isPending: false },
  clone: { mutate: vi.fn(), isPending: false },
}));
vi.mock("@/hooks/useLists", () => ({
  useListCreate: () => h.create,
  useListUpdate: () => h.update,
  useListTemplateClone: () => h.clone,
  useListTemplates: () => ({
    data: { templates: [{ id: "t1", name: "Packing", fields: [] }] },
    isLoading: false,
  }),
}));

import { ListCreateModal } from "@/components/lists/ListCreateModal";
import { ListEditModal } from "@/components/lists/ListEditModal";

beforeEach(() => Object.values(h).forEach((m) => m.mutate.mockReset()));

describe("ListCreateModal", () => {
  it("validates title and creates a custom list", async () => {
    const onClose = vi.fn();
    render(<ListCreateModal open onClose={onClose} communityId="c1" />);
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(await screen.findByText("Title is required")).toBeInTheDocument();
    expect(h.create.mutate).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText("Title"), "Groceries");
    await userEvent.selectOptions(
      screen.getByLabelText("Visibility"),
      "private",
    );
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(h.create.mutate).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Groceries", visibility: "private" }),
      expect.anything(),
    );
  });

  it("requires a template in template mode, then clones", async () => {
    render(<ListCreateModal open onClose={vi.fn()} communityId="c1" />);
    await userEvent.click(screen.getByRole("radio", { name: "From template" }));
    await userEvent.type(screen.getByLabelText("Title"), "Trip");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(await screen.findByText("Choose a template")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Packing" }));
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(h.clone.mutate).toHaveBeenCalledWith(
      { id: "t1", options: { title: "Trip", visibility: "community" } },
      expect.anything(),
    );
  });

  it("cancel closes", async () => {
    const onClose = vi.fn();
    render(<ListCreateModal open onClose={onClose} communityId="c1" />);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalled();
  });
});

describe("ListEditModal", () => {
  it("prefills, validates and updates", async () => {
    render(
      <ListEditModal open onClose={vi.fn()} list={list} communityId="c1" />,
    );
    const title = screen.getByLabelText("Title");
    expect(title).toHaveValue("Camping gear");
    await userEvent.clear(title);
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Title is required")).toBeInTheDocument();
    await userEvent.type(title, "Gear");
    await userEvent.type(screen.getByLabelText("Expires"), "2026-12-31");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(h.update.mutate).toHaveBeenCalledWith(
      {
        id: "l1",
        data: {
          title: "Gear",
          description: "What to bring",
          color: "#3366ff",
          expiresAt: "2026-12-31",
        },
      },
      expect.anything(),
    );
  });
});
