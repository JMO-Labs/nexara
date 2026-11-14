import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TemplateDesigner } from "@/components/lists/TemplateDesigner";
import { TemplatePreview } from "@/components/lists/TemplatePreview";
import { TemplateGallery } from "@/components/lists/TemplateGallery";
import type { TemplateField } from "@/lib/lists/templateModel";

const field = (id: string, label: string): TemplateField => ({
  id,
  key: id,
  label,
  type_key: "text",
  config: {},
  position: 0,
});

describe("TemplateDesigner", () => {
  it("renders fields, preview, and blocks save on empty label", () => {
    const onSave = vi.fn();
    render(
      <TemplateDesigner
        initial={{ name: "T", fields: [field("a", "")] }}
        onSave={onSave}
      />,
    );
    expect(screen.getByTestId("template-preview")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  it("saves valid template and live-updates the preview on label edit", () => {
    const onSave = vi.fn();
    render(
      <TemplateDesigner
        initial={{ name: "T", fields: [field("a", "Name")] }}
        onSave={onSave}
      />,
    );
    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "Renamed" },
    });
    expect(screen.getByTestId("template-preview").textContent).toContain(
      "Renamed",
    );
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "T",
        fields: [expect.objectContaining({ label: "Renamed", position: 0 })],
      }),
    );
  });

  it("deletes a field", () => {
    render(
      <TemplateDesigner
        initial={{ name: "T", fields: [field("a", "Name")] }}
        onSave={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /delete name/i }));
    expect(screen.queryByTestId("field-row-a")).toBeNull();
  });
});

describe("TemplatePreview", () => {
  it("renders labels", () => {
    render(<TemplatePreview fields={[field("a", "Hello")]} />);
    expect(screen.getByText("Hello")).toBeTruthy();
  });
});

describe("TemplateGallery", () => {
  it("fires edit and clone", () => {
    const onEdit = vi.fn();
    const onClone = vi.fn();
    const t = {
      id: "1",
      name: "Pack",
      system: true,
      fields: [field("a", "X")],
    };
    render(
      <TemplateGallery templates={[t]} onEdit={onEdit} onClone={onClone} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /clone pack/i }));
    fireEvent.click(screen.getByRole("button", { name: /edit pack/i }));
    expect(onClone).toHaveBeenCalledWith(t);
    expect(onEdit).toHaveBeenCalledWith(t);
  });
});

describe("TemplateDesigner field config and add flow", () => {
  it("shows the select ConfigEditor and updates preview live", () => {
    render(
      <TemplateDesigner
        initial={{
          name: "T",
          fields: [
            {
              ...field("s", "Pick"),
              type_key: "select",
              config: { options: [] },
            },
          ],
        }}
        onSave={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /add option/i }));
    fireEvent.change(screen.getByLabelText("Value 1"), {
      target: { value: "red" },
    });
    fireEvent.change(screen.getByLabelText("Label 1"), {
      target: { value: "Crimson" },
    });
    expect(screen.getByTestId("template-preview").innerHTML).toContain(
      "Crimson",
    );
  });

  it("adds a field via the Add field modal", () => {
    render(
      <TemplateDesigner
        initial={{ name: "T", fields: [field("a", "First")] }}
        onSave={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /add field/i }));
    fireEvent.click(screen.getByRole("button", { name: /^add$/i }));
    expect(screen.getAllByTestId(/^field-row-/)).toHaveLength(1);
    fireEvent.change(screen.getByLabelText("Key"), { target: { value: "k2" } });
    fireEvent.click(screen.getByRole("button", { name: /^add$/i }));
    expect(screen.getAllByTestId(/^field-row-/)).toHaveLength(1);
    fireEvent.change(screen.getByLabelText("Field label"), {
      target: { value: "Second" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^add$/i }));
    expect(screen.getAllByTestId(/^field-row-/)).toHaveLength(2);
    expect(screen.getByTestId("template-preview").textContent).toContain(
      "Second",
    );
  });
});
