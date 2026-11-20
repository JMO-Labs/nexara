import { describe, it, expect } from "vitest";
import {
  TAB_NAV,
  TOP_NAV,
  MORE_NAV,
  visibleNav,
  isNavActive,
} from "@/components/layout/navItems";

describe("navItems", () => {
  it("tab nav is the single source", () => {
    expect(TAB_NAV.map((i) => i.href)).toEqual([
      "/app",
      "/app/chat",
      "/app/events",
      "/app/photos",
    ]);
    expect(TOP_NAV.map((i) => i.label)).toEqual([
      "Home",
      "Chat",
      "Calendar",
      "Photos",
      "Groups",
    ]);
  });
  it("more nav labels and help action", () => {
    expect(MORE_NAV.map((i) => i.label)).toEqual([
      "People",
      "Lists",
      "Kudos",
      "Saved",
      "Notifications",
      "Settings",
      "Admin",
      "Help",
    ]);
    const help = MORE_NAV.find((i) => i.label === "Help");
    expect(help?.action).toBe("help");
    expect(help?.href).toBeUndefined();
  });
  it("has Saved in more nav", () => {
    expect(MORE_NAV.find((i) => i.label === "Saved")?.href).toBe(
      "/app/bookmarks",
    );
  });
  it("hides Admin for non-admins", () => {
    expect(visibleNav(MORE_NAV, false).map((i) => i.label)).not.toContain(
      "Admin",
    );
    expect(visibleNav(MORE_NAV, true).map((i) => i.label)).toContain("Admin");
  });
  it("has a Lists entry", () => {
    expect(MORE_NAV).toContainEqual(
      expect.objectContaining({ label: "Lists", href: "/app/lists" }),
    );
  });
  it("isNavActive", () => {
    expect(isNavActive("/app/chat/abc", "/app/chat")).toBe(true);
    expect(isNavActive("/app/chat", "/app")).toBe(false);
  });
});

test("isAdmin is role-based", async () => {
  const { isAdmin } = await import("@/components/layout/navItems");
  expect(isAdmin({ role: "admin" })).toBe(true);
  expect(isAdmin({ role: "member" })).toBe(false);
  expect(isAdmin(null)).toBe(false);
});
