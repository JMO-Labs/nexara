/**
 * @file tests/unit/settings/PatternPicker.test.tsx
 * @brief PatternPicker radiogroup behaviour.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PatternPicker } from "@/components/settings/PatternPicker";

describe("PatternPicker", () => {
  it("renders pattern radios with the selected one checked", () => {
    render(
      <PatternPicker
        label="Background pattern"
        value="dots"
        onChange={vi.fn()}
      />,
    );
    const group = screen.getByRole("radiogroup", {
      name: "Background pattern",
    });
    expect(group).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(6);
    expect(screen.getByRole("radio", { name: "Dots" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: "Waves" })).toHaveAttribute(
      "aria-checked",
      "false",
    );
    expect(
      screen.getByRole("radio", { name: "Topographic" }),
    ).toBeInTheDocument();
  });

  it("calls onChange with the chosen pattern", async () => {
    const onChange = vi.fn();
    render(<PatternPicker label="p" value="dots" onChange={onChange} />);
    await userEvent.click(screen.getByRole("radio", { name: "Waves" }));
    expect(onChange).toHaveBeenCalledWith("waves");
  });

  it("offers Community default (null) only when allowed", async () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <PatternPicker label="p" value={null} onChange={onChange} allowDefault />,
    );
    const def = screen.getByRole("radio", { name: "Community default" });
    expect(def).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("radio", { name: "Grain" }));
    rerender(
      <PatternPicker
        label="p"
        value="grain"
        onChange={onChange}
        allowDefault
      />,
    );
    await userEvent.click(
      screen.getByRole("radio", { name: "Community default" }),
    );
    expect(onChange).toHaveBeenLastCalledWith(null);
    rerender(<PatternPicker label="p" value="grain" onChange={onChange} />);
    expect(
      screen.queryByRole("radio", { name: "Community default" }),
    ).toBeNull();
  });
});
