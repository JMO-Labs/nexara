/**
 * @file tests/unit/layout/PageMasthead.test.tsx
 * @brief PageMasthead: title, subtitle (meta) and actions (right) slot.
 */
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { PageMasthead } from "@/components/layout/PageMasthead";
import { renderWithProviders } from "../../utils/renderWithProviders";

describe("PageMasthead", () => {
  it("renders title, meta line and right slot", () => {
    renderWithProviders(
      <PageMasthead
        title="Events"
        meta="12 events this month"
        right={<button type="button">New event</button>}
      />,
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "Events" }),
    ).toBeInTheDocument();
    expect(screen.getByText("12 events this month")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "New event" }),
    ).toBeInTheDocument();
  });

  it("omits optional meta and right slot", () => {
    renderWithProviders(<PageMasthead title="Galleries" />);
    expect(screen.getByRole("heading", { name: "Galleries" })).toBeVisible();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
