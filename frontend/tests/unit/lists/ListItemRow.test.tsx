/**
 * @file tests/unit/lists/ListItemRow.test.tsx
 * @brief ListItemRow: field values, due date, completion + action buttons.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ListItemRow } from "@/components/lists/ListItemRow";
import { fieldsOf } from "@/lib/lists/listFields";
import { fieldSchema, item } from "./listFixtures";

describe("ListItemRow", () => {
  it("renders values via registry views and fires actions", async () => {
    const onToggle = vi.fn();
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    render(
      <ListItemRow
        item={item("i1", "Tent")}
        fields={fieldsOf(fieldSchema)}
        onToggle={onToggle}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );
    expect(screen.getByText("Tent")).toBeInTheDocument();
    expect(screen.getByText(/Due/)).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Complete Tent" }),
    );
    expect(onToggle).toHaveBeenCalledWith(true);
    await userEvent.click(screen.getByRole("button", { name: "Edit Tent" }));
    expect(onEdit).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Delete Tent" }));
    expect(onDelete).toHaveBeenCalled();
  });

  it("fieldsOf accepts camelCase keys and drops invalid rows", () => {
    expect(
      fieldsOf([{ key: "a", label: "A", typeKey: "text" }, { label: "x" }]),
    ).toEqual([
      { key: "a", label: "A", typeKey: "text", required: false, config: {} },
    ]);
  });
});
