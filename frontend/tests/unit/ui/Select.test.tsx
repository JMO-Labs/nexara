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
});
