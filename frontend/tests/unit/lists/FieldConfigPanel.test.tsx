import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FieldConfigPanel } from "@/components/lists/FieldConfigPanel";
import type { TemplateField } from "@/lib/lists/templateModel";

const field = (over: Partial<TemplateField> = {}): TemplateField => ({
  id: "f1",
  key: "k",
  label: "Name",
  type_key: "text",
  config: {},
  position: 0,
  ...over,
});

describe("FieldConfigPanel", () => {
  it("label edit calls onChange with label patch", async () => {
    const onChange = vi.fn();
    render(<FieldConfigPanel field={field()} onChange={onChange} />);
    await userEvent.type(screen.getByRole("textbox", { name: "Label" }), "x");
    expect(onChange).toHaveBeenLastCalledWith({ label: "Namex" });
  });

  it("config edit calls onChange with config patch", async () => {
    const onChange = vi.fn();
    render(<FieldConfigPanel field={field()} onChange={onChange} />);
    await userEvent.click(screen.getByRole("checkbox"));
    expect(onChange).toHaveBeenCalledWith({ config: { multiline: true } });
  });

  it("renders only the label for types without config", () => {
    render(
      <FieldConfigPanel
        field={field({ type_key: "bool" })}
        onChange={vi.fn()}
      />,
    );
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("renders only the label for unknown types", () => {
    render(
      <FieldConfigPanel
        field={field({ type_key: "nope" })}
        onChange={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("region", { name: "Field settings" }),
    ).toBeInTheDocument();
  });
});
