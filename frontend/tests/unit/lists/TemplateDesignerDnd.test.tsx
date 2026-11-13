import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import type { ReactNode } from "react";

let dragEnd: ((e: unknown) => void) | undefined;
vi.mock("@dnd-kit/core", async (orig) => {
  const mod = await orig<typeof import("@dnd-kit/core")>();
  return {
    ...mod,
    DndContext: (p: {
      onDragEnd: (e: unknown) => void;
      children: ReactNode;
    }) => {
      dragEnd = p.onDragEnd;
      return <>{p.children}</>;
    },
  };
});

import { TemplateDesigner } from "@/components/lists/TemplateDesigner";

const f = (id: string, position: number) => ({
  id,
  key: id,
  label: id.toUpperCase(),
  type_key: "text",
  config: {},
  position,
});

describe("TemplateDesigner drag wiring", () => {
  it("DndContext onDragEnd reorders rows and save positions", () => {
    const onSave = vi.fn();
    render(
      <TemplateDesigner
        initial={{ name: "T", fields: [f("a", 0), f("b", 1)] }}
        onSave={onSave}
      />,
    );
    act(() => dragEnd!({ active: { id: "a" }, over: { id: "b" } }));
    const rows = screen.getAllByTestId(/^field-row-/);
    expect(rows.map((r) => r.dataset.testid)).toEqual([
      "field-row-b",
      "field-row-a",
    ]);
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(
      onSave.mock.calls[0][0].fields.map((x: any) => [x.id, x.position]),
    ).toEqual([
      ["b", 0],
      ["a", 1],
    ]);
  });
});
