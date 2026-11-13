/**
 * @file tests/unit/components/layout/SideNav.test.tsx
 * @brief SideNav arrow-key navigation and active indicator.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/navigation", () => ({ usePathname: () => "/app/chat" }));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...r
  }: {
    children: React.ReactNode;
    href: string;
  }) => (
    <a href={href} {...r}>
      {children}
    </a>
  ),
}));

import { SideNav } from "@/components/layout/SideNav";

describe("SideNav", () => {
  it("marks the active link with a 3px left border", () => {
    render(<SideNav />);
    const active = screen.getByRole("link", { current: "page" });
    expect(active.className).toContain("border-l-[3px]");
  });

  it("moves focus with ArrowDown/ArrowUp, wrapping", async () => {
    render(<SideNav />);
    const links = screen.getAllByRole("link");
    links[0].focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(links[1]).toHaveFocus();
    await userEvent.keyboard("{ArrowUp}");
    expect(links[0]).toHaveFocus();
    await userEvent.keyboard("{ArrowUp}");
    expect(links[links.length - 1]).toHaveFocus();
  });
});
