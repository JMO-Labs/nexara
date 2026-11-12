/**
 * @file tests/unit/home/WidgetFrame.test.tsx
 * @brief WidgetFrame: title heading, children, actions.
 */
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { WidgetFrame } from "@/components/home/WidgetFrame";

describe("WidgetFrame", () => {
  it("renders title as h2 and children", () => {
    renderWithProviders(
      <WidgetFrame title="Upcoming">
        <p>body text</p>
      </WidgetFrame>,
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "Upcoming" }),
    ).toBeInTheDocument();
    expect(screen.getByText("body text")).toBeInTheDocument();
  });

  it("renders optional actions", () => {
    renderWithProviders(
      <WidgetFrame title="T" actions={<button>drag</button>}>
        x
      </WidgetFrame>,
    );
    expect(screen.getByRole("button", { name: "drag" })).toBeInTheDocument();
  });
});
