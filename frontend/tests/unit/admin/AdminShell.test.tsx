/**
 * @file tests/unit/admin/AdminShell.test.tsx
 * @brief AdminShell: gated header + grouped side nav with active state.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminActiveId } from "@/components/admin/adminNav";
import { useSession } from "@/stores/session";

const nav = vi.hoisted(() => ({
  path: "/app/admin",
  tab: null as string | null,
}));
vi.mock("next/navigation", () => ({
  usePathname: () => nav.path,
  useSearchParams: () => ({ get: () => nav.tab }),
}));

const GROUPS = ["Community", "People", "Content", "System"];

describe("adminActiveId", () => {
  it("defaults the index route to metrics", () => {
    expect(adminActiveId("/app/admin", null)).toBe("metrics");
  });
  it("uses ?tab= on the index route", () => {
    expect(adminActiveId("/app/admin", "audit-log")).toBe("audit-log");
  });
  it("maps sub-routes to their item", () => {
    expect(adminActiveId("/app/admin/storage", null)).toBe("storage");
    expect(adminActiveId("/app/admin/retention", null)).toBe("retention");
    expect(adminActiveId("/app/admin/moderation", null)).toBe("moderation");
    expect(adminActiveId("/app/admin/plugins", null)).toBe("plugins");
    expect(adminActiveId("/app/admin/plugins/abc", null)).toBe("plugins");
  });
});

describe("AdminShell", () => {
  beforeEach(() => {
    nav.path = "/app/admin";
    nav.tab = null;
    useSession.setState({
      user: { id: "u1", role: "admin" } as never,
      status: "authenticated",
    });
  });

  it("shows only the notice for non-admins", () => {
    useSession.setState({ user: { id: "u2", role: "member" } as never });
    render(<AdminShell>body</AdminShell>);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Admin", level: 1 }),
    ).toBeNull();
    expect(screen.queryByRole("link", { name: "Users" })).toBeNull();
  });

  it("renders the Admin header and four grouped navs", () => {
    render(<AdminShell>body</AdminShell>);
    expect(
      screen.getByRole("heading", { name: "Admin", level: 1 }),
    ).toBeTruthy();
    for (const g of GROUPS)
      expect(screen.getByRole("navigation", { name: g })).toBeTruthy();
  });

  it("wraps the phone nav instead of scrolling it horizontally", () => {
    nav.tab = "audit-log";
    const spy = vi.fn();
    Element.prototype.scrollIntoView = spy;
    render(<AdminShell>body</AdminShell>);
    expect(spy).not.toHaveBeenCalled();
    const wrapper = screen.getByRole("navigation", { name: "Community" })
      .parentElement!.parentElement!;
    expect(wrapper).toHaveClass("max-md:flex-wrap");
    expect(wrapper.className).not.toContain("overflow-x-auto");
  });

  it("has one h1 and a section h2 for the active item", () => {
    nav.tab = "users";
    render(<AdminShell>body</AdminShell>);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(
      screen.getByRole("heading", { level: 2, name: "Users" }),
    ).toBeInTheDocument();
  });

  it("links all 11 tabs plus the 4 route items", () => {
    render(<AdminShell>body</AdminShell>);
    const hrefs = (n: string) =>
      within(screen.getByRole("navigation", { name: n }))
        .getAllByRole("link")
        .map((a) => a.getAttribute("href"));
    const all = GROUPS.flatMap(hrefs);
    expect(all).toHaveLength(15);
    for (const t of [
      "metrics",
      "users",
      "invites",
      "sso",
      "shopping",
      "interests",
      "prompts",
      "branding",
      "ai",
      "audit-log",
      "settings",
    ])
      expect(all).toContain(`/app/admin?tab=${t}`);
    for (const r of ["storage", "retention", "plugins", "moderation"])
      expect(all).toContain(`/app/admin/${r}`);
  });

  it("marks the ?tab= item as current", () => {
    nav.tab = "users";
    render(<AdminShell>body</AdminShell>);
    const cur = screen
      .getAllByRole("link")
      .filter((a) => a.getAttribute("aria-current"));
    expect(cur.map((a) => a.textContent)).toEqual(["Users"]);
  });

  it("marks route items as current and renders children", () => {
    nav.path = "/app/admin/moderation";
    render(<AdminShell>body-here</AdminShell>);
    expect(screen.getByRole("link", { name: "Moderation" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("body-here")).toBeInTheDocument();
  });

  it("keeps onboarding tour hooks on invites, users and sso", () => {
    const { container } = render(<AdminShell>body</AdminShell>);
    for (const t of ["invites", "users", "sso"])
      expect(
        container.querySelector(`[data-tour="admin-${t}"]`),
      ).toHaveAttribute("href", `/app/admin?tab=${t}`);
  });

  it("never uses bg-accent as a selected fill", () => {
    const { container } = render(<AdminShell>body</AdminShell>);
    expect(container.innerHTML).not.toMatch(/bg-accent/);
  });
});
