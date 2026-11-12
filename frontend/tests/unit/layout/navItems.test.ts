import { describe, it, expect } from "vitest";
import {
  PRIMARY_NAV,
  MORE_NAV,
  visibleNav,
  isNavActive,
} from "@/components/layout/navItems";

describe("navItems", () => {
  it("primary labels", () => {
    expect(PRIMARY_NAV.map((i) => i.label)).toEqual([
      "Home",
      "Chat",
      "Calendar",
      "Groups",
    ]);
  });
  it("has Bookmarks in more nav", () => {
    expect(MORE_NAV.find((i) => i.label === "Bookmarks")?.href).toBe(
      "/app/bookmarks",
    );
  });
  it("hides Admin for non-admins", () => {
    expect(visibleNav(MORE_NAV, false).map((i) => i.label)).not.toContain(
      "Admin",
    );
    expect(visibleNav(MORE_NAV, true).map((i) => i.label)).toContain("Admin");
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
