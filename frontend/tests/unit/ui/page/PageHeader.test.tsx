/**
 * @file tests/unit/ui/page/PageHeader.test.tsx
 * @brief PageHeader renders title, description, actions, back link.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "@/components/ui/page";

describe("PageHeader", () => {
  it("renders h1, description and actions", () => {
    render(
      <PageHeader
        title="Photos"
        description="All of them"
        actions={<button>Add</button>}
      />,
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "Photos" }),
    ).toBeInTheDocument();
    expect(screen.getByText("All of them")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
  });
  it("renders back link", () => {
    render(
      <PageHeader title="T" back={{ href: "/app/x", label: "Back to x" }} />,
    );
    expect(screen.getByRole("link", { name: /Back to x/ })).toHaveAttribute(
      "href",
      "/app/x",
    );
  });
});
