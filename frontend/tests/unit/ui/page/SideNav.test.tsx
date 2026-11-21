/**
 * @file tests/unit/ui/page/SideNav.test.tsx
 * @brief SideNav links and active pill.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SideNav } from "@/components/ui/page";

const items = [
  { id: "a", label: "Alpha", href: "/a" },
  { id: "b", label: "Beta", href: "/b" },
];

describe("SideNav", () => {
  it("renders labelled nav with links", () => {
    render(<SideNav items={items} activeId="a" label="Settings" />);
    expect(
      screen.getByRole("navigation", { name: "Settings" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Beta" })).toHaveAttribute(
      "href",
      "/b",
    );
  });
  it("active is ink pill with aria-current", () => {
    render(<SideNav items={items} activeId="a" label="Settings" />);
    const a = screen.getByRole("link", { name: "Alpha" });
    expect(a).toHaveAttribute("aria-current", "page");
    expect(a).toHaveClass("bg-surface-strong", "text-bg");
    expect(screen.getByRole("link", { name: "Beta" })).not.toHaveAttribute(
      "aria-current",
    );
  });
});
