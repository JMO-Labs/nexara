/**
 * @file tests/unit/plugins/ManifestFieldsForm.test.tsx
 * @brief Manifest-driven form: labelled controls, help text, secret handling.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ManifestFieldsForm } from "@/components/plugins/ManifestFieldsForm";
import type { FieldSpec } from "@/lib/api/plugins";

const fields: Record<string, FieldSpec> = {
  on: { type: "boolean", label: "Enabled thing", help: "Help on" },
  mode: {
    type: "select",
    label: "Mode",
    help: "Help mode",
    options: ["a", "b"],
  },
  count: { type: "number", label: "Count", help: "Help count", min: 1, max: 5 },
  name: { type: "string", label: "Name", help: "Help name", max_length: 10 },
  key: { type: "secret", label: "API key", help: "Help key" },
};

describe("ManifestFieldsForm", () => {
  it("labels every control and links help via aria-describedby", () => {
    render(
      <ManifestFieldsForm fields={fields} values={{}} onSubmit={vi.fn()} />,
    );
    for (const [label, help] of [
      ["Enabled thing", "Help on"],
      ["Mode", "Help mode"],
      ["Count", "Help count"],
      ["Name", "Help name"],
      ["API key", "Help key"],
    ]) {
      const el = screen.getByLabelText(label);
      const ids = (el.getAttribute("aria-describedby") ?? "").split(" ");
      const text = ids.map((i) => document.getElementById(i)?.textContent);
      expect(text).toContain(help);
    }
    expect(screen.getByLabelText("Count")).toHaveAttribute("type", "number");
    expect(screen.getByLabelText("Count")).toHaveAttribute("min", "1");
    expect(screen.getByLabelText("Name")).toHaveAttribute("maxlength", "10");
    expect(screen.getByLabelText("API key")).toHaveAttribute(
      "type",
      "password",
    );
    expect(screen.getByLabelText("Enabled thing")).toHaveAttribute(
      "role",
      "switch",
    );
  });

  it("shows saved placeholder for a set secret and submits blank", () => {
    const onSubmit = vi.fn();
    render(
      <ManifestFieldsForm
        fields={{ key: fields.key }}
        values={{ key: { set: true } }}
        onSubmit={onSubmit}
      />,
    );
    const input = screen.getByLabelText("API key");
    expect(input).toHaveAttribute("placeholder", "Saved — leave blank to keep");
    expect(input).toHaveValue("");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).toHaveBeenCalledWith({ key: "" });
  });

  it("submits typed values with numbers coerced", () => {
    const onSubmit = vi.fn();
    render(
      <ManifestFieldsForm
        fields={{ count: fields.count, name: fields.name, on: fields.on }}
        values={{ count: 2, name: "x", on: false }}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText("Count"), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "hi" },
    });
    fireEvent.click(screen.getByLabelText("Enabled thing"));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).toHaveBeenCalledWith({ count: 4, name: "hi", on: true });
  });

  it("clears a typed secret once saved values come back", () => {
    const props = { fields: { key: fields.key }, onSubmit: vi.fn() };
    const { rerender } = render(
      <ManifestFieldsForm {...props} values={{ key: { set: false } }} />,
    );
    const input = screen.getByLabelText("API key");
    fireEvent.change(input, { target: { value: "s3cret" } });
    expect(input).toHaveValue("s3cret");
    rerender(<ManifestFieldsForm {...props} values={{ key: { set: true } }} />);
    expect(screen.getByLabelText("API key")).toHaveValue("");
  });
});
