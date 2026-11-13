import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { fieldRegistry } from "@/lib/lists/fieldRegistry";
import type { FieldType } from "@/lib/lists/fieldTypes/base";

const KEYS = [
  "bool",
  "text",
  "select",
  "multiselect",
  "time",
  "checkbox",
  "date",
  "location",
  "signup",
  "user_pull",
];

describe("fieldRegistry", () => {
  it("has the 10 built-in types", () => {
    expect(fieldRegistry.keys().sort()).toEqual([...KEYS].sort());
  });

  it.each(KEYS)("%s exposes View/Edit/ConfigEditor", (k) => {
    const t = fieldRegistry.get(k)!;
    expect(t.key).toBe(k);
    expect(t.label).toBeTruthy();
    expect(typeof t.View).toBe("function");
    expect(typeof t.Edit).toBe("function");
    expect(typeof t.ConfigEditor).toBe("function");
  });

  it("get returns undefined for unknown; register adds", () => {
    expect(fieldRegistry.get("nope")).toBeUndefined();
    const t = { ...fieldRegistry.get("bool")!, key: "custom" } as FieldType;
    fieldRegistry.register(t);
    expect(fieldRegistry.get("custom")).toBe(t);
  });

  it("is a singleton", async () => {
    const m = await import("@/lib/lists/fieldRegistry");
    expect(m.fieldRegistry).toBe(fieldRegistry);
  });
});

describe("ConfigEditors", () => {
  it("select: add, edit, delete options", () => {
    const onChange = vi.fn();
    const { ConfigEditor } = fieldRegistry.get("select")!;
    render(
      <ConfigEditor
        config={{ options: [{ value: "a", label: "A" }] }}
        onChange={onChange}
      />,
    );
    expect(screen.getByText("Options")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Add Option" }));
    expect(onChange).toHaveBeenLastCalledWith({
      options: [
        { value: "a", label: "A" },
        { value: "", label: "" },
      ],
    });
    fireEvent.change(screen.getByLabelText("Label 1"), {
      target: { value: "Z" },
    });
    expect(onChange).toHaveBeenLastCalledWith({
      options: [{ value: "a", label: "Z" }],
    });
    fireEvent.change(screen.getByLabelText("Value 1"), {
      target: { value: "q" },
    });
    expect(onChange).toHaveBeenLastCalledWith({
      options: [{ value: "q", label: "A" }],
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete option 1" }));
    expect(onChange).toHaveBeenLastCalledWith({ options: [] });
  });

  it("multiselect has the option editor", () => {
    const { ConfigEditor } = fieldRegistry.get("multiselect")!;
    render(<ConfigEditor config={{}} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Add Option" })).toBeTruthy();
  });

  it("date: is_due_field toggle", () => {
    const onChange = vi.fn();
    const { ConfigEditor } = fieldRegistry.get("date")!;
    render(<ConfigEditor config={{}} onChange={onChange} />);
    fireEvent.click(
      screen.getByRole("checkbox", { name: "Is due date field?" }),
    );
    expect(onChange).toHaveBeenCalledWith({ is_due_field: true });
  });

  it("location ConfigEditor renders nothing", () => {
    const { ConfigEditor } = fieldRegistry.get("location")!;
    const { container } = render(
      <ConfigEditor config={{}} onChange={() => {}} />,
    );
    expect(container.innerHTML).toBe("");
  });
});

describe("Views and Edits", () => {
  it("select View shows the option label", () => {
    const { View } = fieldRegistry.get("select")!;
    render(
      <View config={{ options: [{ value: "a", label: "Alpha" }] }} value="a" />,
    );
    expect(screen.getByText("Alpha")).toBeTruthy();
  });

  it("multiselect View lists labels", () => {
    const { View } = fieldRegistry.get("multiselect")!;
    render(
      <View
        config={{
          options: [
            { value: "a", label: "Alpha" },
            { value: "b", label: "Beta" },
          ],
        }}
        value={["a", "b"]}
      />,
    );
    expect(screen.getByText("Alpha")).toBeTruthy();
    expect(screen.getByText("Beta")).toBeTruthy();
  });

  it("multiselect Edit toggles values", () => {
    const onChange = vi.fn();
    const { Edit } = fieldRegistry.get("multiselect")!;
    render(
      <Edit
        config={{ options: [{ value: "a", label: "Alpha" }] }}
        value={[]}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByRole("checkbox", { name: "Alpha" }));
    expect(onChange).toHaveBeenCalledWith(["a"]);
  });

  it("text Edit emits value", () => {
    const onChange = vi.fn();
    const { Edit } = fieldRegistry.get("text")!;
    render(<Edit config={{}} value="" onChange={onChange} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "hi" } });
    expect(onChange).toHaveBeenCalledWith("hi");
  });

  it("date Edit emits value", () => {
    const onChange = vi.fn();
    const { Edit } = fieldRegistry.get("date")!;
    render(<Edit config={{}} value="" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Date"), {
      target: { value: "2026-01-02" },
    });
    expect(onChange).toHaveBeenCalledWith("2026-01-02");
  });

  it("signup View is read-only qty", () => {
    const { View } = fieldRegistry.get("signup")!;
    render(<View config={{}} value={3} />);
    expect(screen.getByText("3")).toBeTruthy();
  });

  it("checkbox ConfigEditor sets completion_mode", () => {
    const onChange = vi.fn();
    const { ConfigEditor } = fieldRegistry.get("checkbox")!;
    render(<ConfigEditor config={{}} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Completion mode"), {
      target: { value: "all" },
    });
    expect(onChange).toHaveBeenCalledWith({ completion_mode: "all" });
  });

  it("bool Edit toggles", () => {
    const onChange = vi.fn();
    const { Edit } = fieldRegistry.get("bool")!;
    render(<Edit config={{}} value={false} onChange={onChange} />);
    fireEvent.click(screen.getByRole("checkbox"));
    expect(onChange).toHaveBeenCalledWith(true);
  });
});
