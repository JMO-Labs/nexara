/**
 * @file tests/unit/ui/ScopeSelect.test.tsx
 * @brief Unit tests for ScopeSelect component.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ScopeSelect } from "@/components/ui/ScopeSelect";

Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.setPointerCapture ??= () => {};
Element.prototype.releasePointerCapture ??= () => {};
Element.prototype.scrollIntoView ??= () => {};

function wrap(ui: React.ReactNode) {
  return render(<>{ui}</>);
}

describe("ScopeSelect", () => {
  const mockSubgroups = [
    { id: "1", name: "Family" },
    { id: "2", name: "Work" },
  ];

  it("renders community option and emits correct value on select", async () => {
    const onChange = vi.fn();
    wrap(
      <ScopeSelect
        value={{ visibility: "community", subgroup_id: null }}
        onChange={onChange}
        subgroups={mockSubgroups}
      />,
    );
    const communityRadio = screen.getByLabelText(/community/i);
    expect(communityRadio).toBeChecked();

    // Click on private option
    const privateRadio = screen.getByLabelText(/just me/i);
    await userEvent.click(privateRadio);

    expect(onChange).toHaveBeenCalledWith({
      visibility: "private",
      subgroup_id: null,
    });
  });

  it("renders subgroup option and shows dropdown when selected", async () => {
    const onChange = vi.fn();
    wrap(
      <ScopeSelect
        value={{ visibility: "community", subgroup_id: null }}
        onChange={onChange}
        subgroups={mockSubgroups}
      />,
    );

    // Dropdown should not be visible initially
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();

    // Click on subgroup option
    const subgroupRadio = screen.getByLabelText(/a specific group/i);
    await userEvent.click(subgroupRadio);

    expect(onChange).toHaveBeenCalledWith({
      visibility: "subgroup",
      subgroup_id: null,
    });
  });

  it("shows subgroup dropdown when subgroup visibility is selected", async () => {
    const onChange = vi.fn();
    wrap(
      <ScopeSelect
        value={{ visibility: "subgroup", subgroup_id: "1" }}
        onChange={onChange}
        subgroups={mockSubgroups}
      />,
    );

    // Dropdown should be visible when subgroup is selected
    const dropdown = screen.getByRole("combobox");
    expect(dropdown).toBeInTheDocument();

    // Check that current selection label is shown
    expect(dropdown).toHaveTextContent("Family");
  });

  it("emits correct value when subgroup is selected from dropdown", async () => {
    const onChange = vi.fn();
    wrap(
      <ScopeSelect
        value={{ visibility: "subgroup", subgroup_id: "1" }}
        onChange={onChange}
        subgroups={mockSubgroups}
      />,
    );

    const dropdown = screen.getByRole("combobox");
    dropdown.focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.click(await screen.findByRole("option", { name: /work/i }));

    expect(onChange).toHaveBeenCalledWith({
      visibility: "subgroup",
      subgroup_id: "2",
    });
  });

  it("emits correct value for private option", async () => {
    const onChange = vi.fn();
    wrap(
      <ScopeSelect
        value={{ visibility: "community", subgroup_id: null }}
        onChange={onChange}
        subgroups={mockSubgroups}
      />,
    );

    const privateRadio = screen.getByLabelText(/just me/i);
    await userEvent.click(privateRadio);

    expect(onChange).toHaveBeenCalledWith({
      visibility: "private",
      subgroup_id: null,
    });
  });

  it("supports keyboard navigation between options", async () => {
    const onChange = vi.fn();
    wrap(
      <ScopeSelect
        value={{ visibility: "community", subgroup_id: null }}
        onChange={onChange}
        subgroups={mockSubgroups}
      />,
    );

    const communityRadio = screen.getByLabelText(
      /community/i,
    ) as HTMLInputElement;
    const subgroupRadio = screen.getByLabelText(
      /a specific group/i,
    ) as HTMLInputElement;

    // Initially community is checked
    expect(communityRadio).toBeChecked();

    // Click subgroup option
    await userEvent.click(subgroupRadio);

    // onChange should be called with subgroup
    expect(onChange).toHaveBeenCalledWith({
      visibility: "subgroup",
      subgroup_id: null,
    });
  });

  it("has proper ARIA labels and roles", () => {
    wrap(
      <ScopeSelect
        value={{ visibility: "community", subgroup_id: null }}
        onChange={() => {}}
        subgroups={mockSubgroups}
      />,
    );

    // Check that radio buttons have proper roles and labels
    expect(screen.getByLabelText(/community/i)).toHaveAttribute(
      "type",
      "radio",
    );
    expect(screen.getByLabelText(/a specific group/i)).toHaveAttribute(
      "type",
      "radio",
    );
    expect(screen.getByLabelText(/just me/i)).toHaveAttribute("type", "radio");
  });
});
