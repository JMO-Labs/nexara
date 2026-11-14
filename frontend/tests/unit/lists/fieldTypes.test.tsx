import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fieldRegistry } from "@/lib/lists/fieldRegistry";
import { optionsOf, str } from "@/lib/lists/fieldTypes/base";

const T = (k: string) => fieldRegistry.get(k)!;
const opts = {
  options: [
    { value: "a", label: "Alpha" },
    { value: "b", label: "" },
  ],
};

describe("base helpers", () => {
  it("optionsOf is safe and str stringifies", () => {
    expect(optionsOf({})).toEqual([]);
    expect(optionsOf({ options: "x" })).toEqual([]);
    expect(str(null)).toBe("");
    expect(str(5)).toBe("5");
  });
});

describe("View", () => {
  it.each([
    ["bool", {}, true, "Yes"],
    ["bool", {}, false, "No"],
    ["checkbox", {}, true, "Done"],
    ["checkbox", {}, false, "Not done"],
    ["text", {}, "hi", "hi"],
    ["text", {}, null, "—"],
    ["time", {}, "10:30", "10:30"],
    ["date", {}, "2026-01-02", "2026-01-02"],
    ["select", opts, "a", "Alpha"],
    ["select", opts, "b", "b"],
    ["select", opts, "zz", "—"],
    ["signup", {}, 3, "3"],
    ["signup", {}, undefined, "0"],
    ["user_pull", {}, "Ann", "Ann"],
    ["location", {}, null, "—"],
    [
      "location",
      {},
      { address: "1 Main", lat: "1", lng: "2" },
      "1 Main (1, 2)",
    ],
    ["location", {}, { address: "1 Main" }, "1 Main"],
    ["multiselect", opts, [], "—"],
  ])("%s renders %j -> %s", (k, config, value, text) => {
    const View = T(k).View;
    render(<View config={config} value={value} />);
    expect(screen.getByText(text as string)).toBeInTheDocument();
  });

  it("multiselect lists labels with value fallback", () => {
    const View = T("multiselect").View;
    render(<View config={opts} value={["a", "b", "c"]} />);
    expect(screen.getAllByRole("listitem").map((l) => l.textContent)).toEqual([
      "Alpha",
      "b",
      "c",
    ]);
  });
});

describe("Edit", () => {
  it("bool toggles", async () => {
    const onChange = vi.fn();
    const Edit = T("bool").Edit;
    render(<Edit config={{}} value={false} onChange={onChange} />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Value" }));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("checkbox toggles off", async () => {
    const onChange = vi.fn();
    const Edit = T("checkbox").Edit;
    render(<Edit config={{}} value={true} onChange={onChange} label="Ok" />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Ok" }));
    expect(onChange).toHaveBeenCalledWith(false);
  });

  it("text uses input or textarea by config", async () => {
    const onChange = vi.fn();
    const Edit = T("text").Edit;
    const { rerender } = render(
      <Edit config={{}} value="" onChange={onChange} />,
    );
    await userEvent.type(screen.getByRole("textbox", { name: "Text" }), "a");
    expect(onChange).toHaveBeenCalledWith("a");
    rerender(
      <Edit config={{ multiline: true }} value="" onChange={onChange} />,
    );
    expect(screen.getByRole("textbox").tagName).toBe("TEXTAREA");
  });

  it.each([
    ["time", "Time", "10:30"],
    ["date", "Date", "2026-01-02"],
  ])("%s input emits value", (k, name, v) => {
    const onChange = vi.fn();
    const Edit = T(k).Edit;
    render(<Edit config={{}} value="" onChange={onChange} />);
    // fireEvent-free: set via userEvent.type on time/date is flaky in jsdom
    const el = screen.getByLabelText(name) as HTMLInputElement;
    const set = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    )!.set!;
    set.call(el, v);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    expect(onChange).toHaveBeenCalledWith(v);
  });

  it("location merges partial edits", async () => {
    const onChange = vi.fn();
    const Edit = T("location").Edit;
    render(<Edit config={{}} value={{ address: "A" }} onChange={onChange} />);
    await userEvent.type(
      screen.getByRole("textbox", { name: "Latitude" }),
      "5",
    );
    expect(onChange).toHaveBeenLastCalledWith({ address: "A", lat: "5" });
    await userEvent.type(
      screen.getByRole("textbox", { name: "Longitude" }),
      "6",
    );
    expect(onChange).toHaveBeenLastCalledWith({ address: "A", lng: "6" });
    await userEvent.type(screen.getByRole("textbox", { name: "Address" }), "b");
    expect(onChange).toHaveBeenLastCalledWith({ address: "Ab" });
  });

  it("multiselect adds and removes values, hides empty values", async () => {
    const onChange = vi.fn();
    const Edit = T("multiselect").Edit;
    const cfg = { options: [...opts.options, { value: "", label: "blank" }] };
    const { rerender } = render(
      <Edit config={cfg} value={["b"]} onChange={onChange} />,
    );
    expect(screen.queryByRole("checkbox", { name: "blank" })).toBeNull();
    await userEvent.click(screen.getByRole("checkbox", { name: "Alpha" }));
    expect(onChange).toHaveBeenCalledWith(["b", "a"]);
    rerender(<Edit config={cfg} value={["a", "b"]} onChange={onChange} />);
    await userEvent.click(screen.getByRole("checkbox", { name: "b" }));
    expect(onChange).toHaveBeenLastCalledWith(["a"]);
  });

  it("select renders a combobox with label", () => {
    const Edit = T("select").Edit;
    render(<Edit config={opts} value="a" onChange={vi.fn()} label="Pick" />);
    expect(screen.getByRole("combobox", { name: "Pick" })).toBeInTheDocument();
  });

  it.each(["signup", "user_pull"])("%s edit is read-only text", (k) => {
    const Edit = T(k).Edit;
    render(<Edit config={{}} value="v" onChange={vi.fn()} />);
    expect(screen.getByText("v")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
  });
});

describe("ConfigEditor", () => {
  it.each(["bool", "time", "location", "signup"])("%s renders nothing", (k) => {
    const C = T(k).ConfigEditor;
    const { container } = render(<C config={{}} onChange={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("text toggles multiline", async () => {
    const onChange = vi.fn();
    const C = T("text").ConfigEditor;
    render(<C config={{ x: 1 }} onChange={onChange} />);
    await userEvent.click(screen.getByRole("checkbox"));
    expect(onChange).toHaveBeenCalledWith({ x: 1, multiline: true });
  });

  it("date toggles is_due_field", async () => {
    const onChange = vi.fn();
    const C = T("date").ConfigEditor;
    render(<C config={{}} onChange={onChange} />);
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Is due date field?" }),
    );
    expect(onChange).toHaveBeenCalledWith({ is_due_field: true });
  });

  it("checkbox sets completion_mode", async () => {
    const onChange = vi.fn();
    const C = T("checkbox").ConfigEditor;
    render(<C config={{}} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByRole("combobox"), "all");
    expect(onChange).toHaveBeenCalledWith({ completion_mode: "all" });
  });

  it("user_pull edits source", async () => {
    const onChange = vi.fn();
    const C = T("user_pull").ConfigEditor;
    render(<C config={{ source: "d" }} onChange={onChange} />);
    await userEvent.type(
      screen.getByRole("textbox", { name: /User attribute/ }),
      "x",
    );
    expect(onChange).toHaveBeenCalledWith({ source: "dx" });
  });

  it.each(["select", "multiselect"])("%s edits options", async (k) => {
    const onChange = vi.fn();
    const C = T(k).ConfigEditor;
    render(
      <C
        config={{ options: [{ value: "a", label: "A" }] }}
        onChange={onChange}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Add Option/ }));
    expect(onChange).toHaveBeenLastCalledWith({
      options: [
        { value: "a", label: "A" },
        { value: "", label: "" },
      ],
    });
    await userEvent.type(screen.getByRole("textbox", { name: "Value 1" }), "z");
    expect(onChange).toHaveBeenLastCalledWith({
      options: [{ value: "az", label: "A" }],
    });
    await userEvent.type(screen.getByRole("textbox", { name: "Label 1" }), "z");
    expect(onChange).toHaveBeenLastCalledWith({
      options: [{ value: "a", label: "Az" }],
    });
    await userEvent.click(
      screen.getByRole("button", { name: "Delete option 1" }),
    );
    expect(onChange).toHaveBeenLastCalledWith({ options: [] });
  });
});
