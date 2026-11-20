/**
 * @file tests/unit/ui/page/Segmented.test.tsx
 * @brief Segmented radiogroup semantics and keyboard.
 */
import { describe, it, expect, vi } from "vitest";
import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Segmented } from "@/components/ui/page";

const opts = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Beta" },
  { value: "c", label: "Gamma" },
] as const;

describe("Segmented", () => {
  it("renders radiogroup with aria-checked and roving tabindex", () => {
    render(
      <Segmented
        options={[...opts]}
        value="b"
        onChange={() => {}}
        label="View"
      />,
    );
    expect(
      screen.getByRole("radiogroup", { name: "View" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Beta" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: "Alpha" })).toHaveAttribute(
      "aria-checked",
      "false",
    );
    expect(screen.getByRole("radio", { name: "Beta" })).toHaveAttribute(
      "tabindex",
      "0",
    );
    expect(screen.getByRole("radio", { name: "Alpha" })).toHaveAttribute(
      "tabindex",
      "-1",
    );
  });
  it("active pill is ink", () => {
    render(
      <Segmented
        options={[...opts]}
        value="a"
        onChange={() => {}}
        label="View"
      />,
    );
    expect(screen.getByRole("radio", { name: "Alpha" })).toHaveClass(
      "bg-surface-strong",
      "text-bg",
    );
  });
  it("click selects", async () => {
    const onChange = vi.fn();
    render(
      <Segmented
        options={[...opts]}
        value="a"
        onChange={onChange}
        label="View"
      />,
    );
    await userEvent.click(screen.getByRole("radio", { name: "Gamma" }));
    expect(onChange).toHaveBeenCalledWith("c");
  });
  it("arrow keys move selection and wrap", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    function Wrapper() {
      const [v, setV] = useState<"a" | "b" | "c">("a");
      return (
        <Segmented
          options={[...opts]}
          value={v}
          onChange={(x) => {
            onChange(x);
            setV(x);
          }}
          label="View"
        />
      );
    }
    render(<Wrapper />);
    await user.tab();
    expect(screen.getByRole("radio", { name: "Alpha" })).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(onChange).toHaveBeenLastCalledWith("b");
    expect(screen.getByRole("radio", { name: "Beta" })).toHaveFocus();
    await user.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(onChange).toHaveBeenLastCalledWith("c");
  });
});
