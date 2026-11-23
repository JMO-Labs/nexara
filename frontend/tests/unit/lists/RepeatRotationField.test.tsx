/**
 * @file tests/unit/lists/RepeatRotationField.test.tsx
 * @brief Chore field: repeat select, keyboard-friendly reorder, add/remove,
 *        and the setChore client path.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const m = vi.hoisted(() => ({ apiPut: vi.fn() }));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  ...m,
}));

import {
  RepeatRotationField,
  moveItem,
} from "@/components/lists/RepeatRotationField";
import { listApi } from "@/lib/api/lists";
import { ListItemRow } from "@/components/lists/ListItemRow";
import { item } from "./listFixtures";

const people = [
  { id: "a", name: "Maya" },
  { id: "b", name: "Sam" },
  { id: "c", name: "Ruth" },
];

beforeEach(() => m.apiPut.mockReset());

describe("RepeatRotationField", () => {
  it("hides rotation until a repeat is chosen, clears it on Never", async () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <RepeatRotationField
        value={{ repeat: null, rotation: [] }}
        onChange={onChange}
        people={people}
      />,
    );
    expect(screen.queryByText("Takes turns in this order.")).toBeNull();
    await userEvent.selectOptions(screen.getByLabelText("Repeat"), "weekly");
    expect(onChange).toHaveBeenCalledWith({ repeat: "weekly", rotation: [] });
    rerender(
      <RepeatRotationField
        value={{ repeat: "weekly", rotation: ["a"] }}
        onChange={onChange}
        people={people}
      />,
    );
    await userEvent.selectOptions(screen.getByLabelText("Repeat"), "");
    expect(onChange).toHaveBeenLastCalledWith({ repeat: null, rotation: [] });
  });

  it("reorders with buttons, removes and adds", async () => {
    const onChange = vi.fn();
    render(
      <RepeatRotationField
        value={{ repeat: "daily", rotation: ["a", "b"] }}
        onChange={onChange}
        people={people}
      />,
    );
    expect(screen.getByRole("button", { name: "Move Maya up" })).toBeDisabled();
    await userEvent.click(
      screen.getByRole("button", { name: "Move Maya down" }),
    );
    expect(onChange).toHaveBeenLastCalledWith({
      repeat: "daily",
      rotation: ["b", "a"],
    });
    await userEvent.click(
      screen.getByRole("button", { name: "Remove Sam from rotation" }),
    );
    expect(onChange).toHaveBeenLastCalledWith({
      repeat: "daily",
      rotation: ["a"],
    });
    await userEvent.selectOptions(
      screen.getByLabelText("Add person to rotation"),
      "c",
    );
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(onChange).toHaveBeenLastCalledWith({
      repeat: "daily",
      rotation: ["a", "b", "c"],
    });
  });

  it("moveItem ignores out-of-range moves", () => {
    expect(moveItem(["a", "b"], 0, -1)).toEqual(["a", "b"]);
    expect(moveItem(["a", "b"], 0, 1)).toEqual(["b", "a"]);
  });
});

describe("listApi.setChore", () => {
  it("PUTs /api/v1/lists/:id/items/:id/chore with snake_case body", async () => {
    m.apiPut.mockResolvedValue({ id: "i1", next_assignee: { id: "b" } });
    const r = await listApi.setChore("l1", "i1", {
      repeat: "weekly",
      rotation: ["a", "b"],
    });
    expect(m.apiPut).toHaveBeenCalledWith("/api/v1/lists/l1/items/i1/chore", {
      repeat: "weekly",
      rotation: ["a", "b"],
    });
    expect(r.nextAssignee).toMatchObject({ id: "b" });
  });
});

describe("ListItemRow next-up", () => {
  it("shows who is next and the weekday", () => {
    render(
      <ListItemRow
        item={{
          ...item("i1", "Trash"),
          repeat: "weekly",
          nextDueAt: "2026-11-29T12:00:00Z",
          nextAssignee: { id: "a", displayName: "Maya" },
        }}
        fields={[]}
        onToggle={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/Next: Maya/)).toHaveTextContent(/Sun/);
  });
});
