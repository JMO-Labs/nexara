/**
 * @file tests/unit/layout/PageMasthead.test.tsx
 * @brief PageMasthead title, meta line and right slot.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageMasthead } from "@/components/layout/PageMasthead";

describe("PageMasthead", () => {
  it("renders title, meta and right slot", () => {
    render(
      <PageMasthead
        title="Events"
        meta="12 events this month"
        right={<button>New event</button>}
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

  it("omits meta and right slot when not provided", () => {
    render(<PageMasthead title="Galleries" />);
    expect(
      screen.getByRole("heading", { name: "Galleries" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("applies the md size class", () => {
    render(<PageMasthead title="T" size="md" />);
    expect(screen.getByRole("heading").className).toContain("md:text-[92px]");
  });
});
