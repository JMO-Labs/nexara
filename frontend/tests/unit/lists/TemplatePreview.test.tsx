import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TemplatePreview } from "@/components/lists/TemplatePreview";
import type { TemplateField } from "@/lib/lists/templateModel";

const f = (
  type_key: string,
  label: string,
  config: Record<string, unknown> = {},
): TemplateField => ({
  id: label,
  key: label,
  label,
  type_key,
  config,
  position: 0,
});

describe("TemplatePreview", () => {
  it("renders an input per field type", () => {
    render(
      <TemplatePreview
        fields={[
          f("bool", "Bool"),
          f("text", "Text"),
          f("time", "Time"),
          f("date", "Date"),
          f("checkbox", "Check"),
          f("location", "Loc"),
          f("multiselect", "Multi", {
            options: [{ value: "a", label: "Alpha" }],
          }),
          f("select", "Sel", { options: [{ value: "b", label: "Beta" }] }),
        ]}
      />,
    );
    expect(screen.getByRole("checkbox", { name: "Bool" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Text" })).toBeInTheDocument();
    expect(screen.getByLabelText("Time")).toHaveAttribute("type", "time");
    expect(screen.getByLabelText("Date")).toHaveAttribute("type", "date");
    expect(screen.getByRole("checkbox", { name: "Check" })).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Address" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Sel" })).toBeInTheDocument();
  });

  it("shows option hints and skips empty options", () => {
    render(
      <TemplatePreview
        fields={[
          f("select", "Sel", {
            options: [
              { value: "b", label: "Beta" },
              { value: "", label: "" },
            ],
          }),
        ]}
      />,
    );
    const hints = screen.getByRole("list", { name: "Sel options" });
    expect(hints.children).toHaveLength(1);
    expect(hints).toHaveTextContent("Beta");
  });

  it("tolerates unknown types and shows the label", () => {
    render(<TemplatePreview fields={[f("nope", "Mystery")]} />);
    expect(screen.getByText("Mystery")).toBeInTheDocument();
  });

  it("renders signup and user_pull as read-only text", () => {
    render(
      <TemplatePreview fields={[f("signup", "Qty"), f("user_pull", "Who")]} />,
    );
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
