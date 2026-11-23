/**
 * @file tests/unit/ui/SettingsRow.test.tsx
 * @brief Test SettingsRow primitive with two-column responsive layout.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SettingsRow } from "@/components/ui/SettingsRow";

function wrap(ui: React.ReactNode) {
  return render(<>{ui}</>);
}

describe("SettingsRow", () => {
  it("renders label and children", () => {
    wrap(
      <SettingsRow label="Dark mode">
        <input type="checkbox" />
      </SettingsRow>,
    );
    expect(screen.getByText("Dark mode")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    wrap(
      <SettingsRow label="Theme" description="Choose your preferred appearance">
        <div>controls</div>
      </SettingsRow>,
    );
    expect(screen.getByText("Theme")).toBeInTheDocument();
    expect(
      screen.getByText("Choose your preferred appearance"),
    ).toBeInTheDocument();
  });

  it("does not render description when not provided", () => {
    wrap(
      <SettingsRow label="Name">
        <input />
      </SettingsRow>,
    );
    expect(screen.getByText("Name")).toBeInTheDocument();
  });

  it("renders children with correct content", () => {
    wrap(
      <SettingsRow label="Email">
        <input value="test@example.com" readOnly />
      </SettingsRow>,
    );
    const input = screen.getByDisplayValue("test@example.com");
    expect(input).toBeInTheDocument();
  });

  it("uses a fixed label column and fluid control from md", () => {
    const { container } = wrap(
      <SettingsRow label="Email" description="d">
        <input />
      </SettingsRow>,
    );
    const row = container.firstElementChild as HTMLElement;
    expect(row).toHaveClass(
      "grid-cols-1",
      "md:grid-cols-[13rem_minmax(0,1fr)]",
    );
    expect(row).toHaveClass("md:items-center");
  });

  it("description uses AA-safe muted color, not opacity", () => {
    wrap(
      <SettingsRow label="A" description="help">
        <input />
      </SettingsRow>,
    );
    const d = screen.getByText("help");
    expect(d).toHaveClass("text-muted");
    expect(d.className).not.toMatch(/opacity/);
  });
});
