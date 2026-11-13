/**
 * @file tests/unit/layout/SideNav.test.tsx
 * @brief SideNav links, active state, admin gating, focus expand/collapse.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SideNav } from "@/components/layout/SideNav";
import { useSession } from "@/stores/session";
import type { CurrentUser } from "@/lib/api/users";

vi.mock("next/navigation", () => ({ usePathname: vi.fn() }));
import { usePathname } from "next/navigation";

const user = (admin: boolean) =>
  ({
    id: "1",
    role: admin ? "admin" : "member",
  }) as CurrentUser;

describe("SideNav", () => {
  beforeEach(() => {
    vi.mocked(usePathname).mockReturnValue("/app/events");
    useSession.getState().setUser(user(false));
  });

  it("renders all visible items as links", () => {
    render(<SideNav />);
    for (const n of [
      "Home",
      "Chat",
      "Calendar",
      "Groups",
      "Galleries",
      "Media",
      "Bookmarks",
      "Members",
      "Notifications",
      "Settings",
      "Help",
    ]) {
      expect(screen.getByRole("link", { name: n })).toBeInTheDocument();
    }
  });

  it("marks active link", () => {
    render(<SideNav />);
    expect(screen.getByRole("link", { name: "Calendar" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("hides Admin for non-admin", () => {
    render(<SideNav />);
    expect(screen.queryByRole("link", { name: "Admin" })).toBeNull();
  });

  it("shows Admin for admin", () => {
    useSession.getState().setUser(user(true));
    render(<SideNav />);
    expect(screen.getByRole("link", { name: "Admin" })).toBeInTheDocument();
  });

  it("expands on focus and collapses on Escape", () => {
    render(<SideNav />);
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(nav).toHaveAttribute("data-expanded", "false");
    fireEvent.focus(screen.getByRole("link", { name: "Home" }));
    expect(nav).toHaveAttribute("data-expanded", "true");
    fireEvent.keyDown(nav, { key: "Escape" });
    expect(nav).toHaveAttribute("data-expanded", "false");
  });

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
