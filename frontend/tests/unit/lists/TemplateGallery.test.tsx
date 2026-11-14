import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TemplateGallery } from "@/components/lists/TemplateGallery";
import type { ListTemplate } from "@/lib/lists/templateModel";

const tpls: ListTemplate[] = [
  {
    id: "t1",
    name: "Potluck",
    system: true,
    fields: [
      {
        id: "a",
        key: "dish",
        label: "Dish",
        type_key: "text",
        config: {},
        position: 0,
      },
    ],
  },
  { id: "t2", name: "Chores", fields: [] },
];

describe("TemplateGallery", () => {
  it("renders each template and the System badge", () => {
    render(
      <TemplateGallery templates={tpls} onEdit={vi.fn()} onClone={vi.fn()} />,
    );
    expect(screen.getAllByRole("listitem").length).toBeGreaterThanOrEqual(2);
    expect(
      screen.getByRole("heading", { name: /Potluck/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Chores/ })).toBeInTheDocument();
    expect(screen.getAllByText("System")).toHaveLength(1);
  });

  it("fires edit and clone handlers with the template", async () => {
    const onEdit = vi.fn();
    const onClone = vi.fn();
    render(
      <TemplateGallery templates={tpls} onEdit={onEdit} onClone={onClone} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Edit Chores" }));
    await userEvent.click(
      screen.getByRole("button", { name: "Clone Potluck" }),
    );
    expect(onEdit).toHaveBeenCalledWith(tpls[1]);
    expect(onClone).toHaveBeenCalledWith(tpls[0]);
  });

  it("renders an empty list without templates", () => {
    render(
      <TemplateGallery templates={[]} onEdit={vi.fn()} onClone={vi.fn()} />,
    );
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });
});
