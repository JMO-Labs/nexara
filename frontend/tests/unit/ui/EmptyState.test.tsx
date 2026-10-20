/**
 * @file tests/unit/ui/EmptyState.test.tsx
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "@/components/ui/EmptyState";

describe("EmptyState", () => {
  it("renders title, description, action", () => {
    render(
      <EmptyState
        title="Quiet here"
        description="No posts yet."
        action={<button>Write one</button>}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Quiet here" }),
    ).toBeInTheDocument();
    expect(screen.getByText("No posts yet.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /write one/i }),
    ).toBeInTheDocument();
  });
});
