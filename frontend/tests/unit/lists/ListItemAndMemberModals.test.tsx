/**
 * @file tests/unit/lists/ListItemAndMemberModals.test.tsx
 * @brief Item edit modal (dynamic fields, required validation) and
 *        member manage modal (add/remove, validation).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fieldSchema, item } from "./listFixtures";
import { fieldsOf } from "@/lib/lists/listFields";

const h = vi.hoisted(() => ({
  create: { mutate: vi.fn(), isPending: false },
  update: { mutate: vi.fn(), isPending: false },
  add: { mutate: vi.fn(), isPending: false },
  remove: { mutate: vi.fn(), isPending: false },
}));
vi.mock("@/hooks/useLists", () => ({ useListItemCreate: () => h.create }));
vi.mock("@/hooks/useListActions", () => ({
  useListItemUpdate: () => h.update,
  useListMemberAdd: () => h.add,
  useListMemberRemove: () => h.remove,
  useListMembers: () => ({
    data: [{ listId: "l1", userId: "u9", role: "editor", sharePersonal: true }],
    isLoading: false,
  }),
}));

import { ListItemEditModal } from "@/components/lists/ListItemEditModal";
import { ListMemberManageModal } from "@/components/lists/ListMemberManageModal";

const fields = fieldsOf(fieldSchema);
const UID = "123e4567-e89b-42d3-a456-426614174000";

beforeEach(() => Object.values(h).forEach((m) => m.mutate.mockReset()));

describe("ListItemEditModal", () => {
  it("requires required fields, then creates", async () => {
    render(
      <ListItemEditModal
        open
        onClose={vi.fn()}
        listId="l1"
        fields={fields}
        nextPosition={4}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Name is required")).toBeInTheDocument();
    expect(h.create.mutate).not.toHaveBeenCalled();
    await userEvent.type(screen.getByRole("textbox", { name: "Name" }), "Tent");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(h.create.mutate).toHaveBeenCalledWith(
      { position: 4, values: { name: "Tent" } },
      expect.anything(),
    );
  });

  it("edits an existing item", async () => {
    render(
      <ListItemEditModal
        open
        onClose={vi.fn()}
        listId="l1"
        fields={fields}
        item={item("i1", "Tent")}
      />,
    );
    expect(screen.getByRole("dialog")).toHaveTextContent("Edit item");
    await userEvent.type(screen.getByRole("textbox", { name: "Name" }), "s");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(h.update.mutate).toHaveBeenCalledWith(
      { itemId: "i1", values: { name: "Tents", done: true } },
      expect.anything(),
    );
  });
});

describe("ListMemberManageModal", () => {
  it("lists members, removes, validates and adds", async () => {
    render(<ListMemberManageModal open onClose={vi.fn()} listId="l1" />);
    expect(screen.getByText("u9")).toBeInTheDocument();
    expect(screen.getByText("Shares personal info")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Remove u9" }));
    expect(h.remove.mutate).toHaveBeenCalledWith("u9");
    await userEvent.type(screen.getByLabelText("User ID"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(
      await screen.findByText("Enter a valid user ID"),
    ).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("User ID"));
    await userEvent.type(screen.getByLabelText("User ID"), UID);
    await userEvent.selectOptions(screen.getByLabelText("Role"), "editor");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(h.add.mutate).toHaveBeenCalledWith(
      { userId: UID, role: "editor" },
      expect.anything(),
    );
  });
});
