/**
 * @file tests/unit/admin/ColorPicker.test.tsx
 * @brief ColorPicker hex validation and FontPicker preview.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { ColorPicker } from "@/components/admin/ColorPicker";
import { FontPicker } from "@/components/admin/FontPicker";

function Harness({ onChange }: { onChange?: (v: string) => void }) {
  const [v, setV] = useState("#ffffff");
  return (
    <ColorPicker
      label="Surface (light)"
      value={v}
      onChange={(x) => {
        setV(x);
        onChange?.(x);
      }}
    />
  );
}

describe("ColorPicker", () => {
  it("renders hex input and swatch picker", () => {
    render(<Harness />);
    expect(screen.getByLabelText("Surface (light)")).toHaveValue("#ffffff");
    expect(screen.getByLabelText("Surface (light) picker")).toBeInTheDocument();
  });

  it("flags invalid hex", async () => {
    render(<Harness />);
    const input = screen.getByLabelText("Surface (light)");
    await userEvent.clear(input);
    await userEvent.type(input, "#12");
    expect(screen.getByText(/#RRGGBB/)).toBeInTheDocument();
  });
});

describe("FontPicker", () => {
  it("shows a preview in the chosen family", () => {
    render(
      <FontPicker label="Font" value="Inter" onChange={vi.fn()} kind="sans" />,
    );
    expect(screen.getByTestId("font-preview")).toHaveStyle({
      fontFamily: "Inter, system-ui, sans-serif",
    });
  });
});
