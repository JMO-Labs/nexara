/**
 * @file tests/unit/ui/page/Panel.test.tsx
 * @brief Panel glass surface.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Calendar } from "lucide-react";
import { Panel } from "@/components/ui/page";

describe("Panel", () => {
  it("renders glass section with title, icon, actions", () => {
    render(
      <Panel
        title="Upcoming"
        icon={Calendar}
        actions={<button>Go</button>}
        data-testid="p"
      >
        body
      </Panel>,
    );
    const el = screen.getByTestId("p");
    expect(el.tagName).toBe("SECTION");
    expect(el).toHaveClass("glass", "rounded-[32px]");
    expect(
      screen.getByRole("heading", { name: "Upcoming" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
    expect(screen.getByText("body")).toBeInTheDocument();
  });
  it("as=div renders a div", () => {
    render(
      <Panel as="div" data-testid="p">
        x
      </Panel>,
    );
    expect(screen.getByTestId("p").tagName).toBe("DIV");
  });
});
