/**
 * @file tests/unit/ui/Select.test.tsx
 * @brief Select opens by keyboard and reports chosen value.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Select, Option } from "@/components/ui/Select";

Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.setPointerCapture ??= () => {};
Element.prototype.releasePointerCapture ??= () => {};
Element.prototype.scrollIntoView ??= () => {};

describe("Select", () => {
  it("chooses an option via keyboard", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    render(
      <Select label="Repeat" placeholder="Pick" onValueChange={onValueChange}>
        <Option value="daily">Daily</Option>
        <Option value="weekly">Weekly</Option>
      </Select>,
    );
    screen.getByRole("combobox").focus();
    await user.keyboard("{Enter}");
    await user.click(await screen.findByRole("option", { name: "Weekly" }));
    expect(onValueChange).toHaveBeenCalledWith("weekly");
  });

  it("applies a className to the trigger", () => {
    render(
      <Select label="Group" className="rounded-full">
        <Option value="a">A</Option>
      </Select>,
    );
    const trigger = screen.getByRole("combobox", { name: "Group" });
    expect(trigger).toHaveClass("rounded-full");
    expect(trigger).not.toHaveClass("rounded-md");
  });

  it("trigger matches the input pill (no square shadcn box)", () => {
    render(
      <Select label="Visibility">
        <Option value="a">A</Option>
      </Select>,
    );
    const trigger = screen.getByRole("combobox", { name: "Visibility" });
    expect(trigger).toHaveClass("rounded-full");
    expect(trigger).not.toHaveClass("rounded-md");
    expect(trigger).not.toHaveClass("border-input");
    expect(trigger).not.toHaveClass("shadow-xs");
    expect(trigger).toHaveClass("data-[size=default]:h-11");
  });
});
