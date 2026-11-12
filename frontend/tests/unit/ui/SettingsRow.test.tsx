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

  it("uses a 12-col grid: label 4/12, control 8/12 from md", () => {
    const { container } = wrap(
      <SettingsRow label="Email" description="d">
        <input />
      </SettingsRow>,
    );
    const row = container.firstElementChild as HTMLElement;
    expect(row).toHaveClass("grid-cols-1", "md:grid-cols-12");
    expect(row.children[0]).toHaveClass("md:col-span-4");
    expect(row.children[1]).toHaveClass("md:col-span-8");
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
