/**
 * @file tests/unit/layout/navItems.test.ts
 * @brief Nav config: top/more items, legacy match prefixes, active checks.
 */
import { describe, it, expect } from "vitest";
import {
  TAB_NAV,
  TOP_NAV,
  MORE_NAV,
  PHONE_EXTRA_NAV,
  visibleNav,
  isNavActive,
  isItemActive,
} from "@/components/layout/navItems";

const find = (items: typeof TOP_NAV, label: string) =>
  items.find((i) => i.label === label)!;

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
      "Community",
      "Wishlists",
      "Inbox",
    ]);
  });
  it("Community is the top item and matches legacy routes", () => {
    const community = find(TOP_NAV, "Community");
    expect(community.href).toBe("/app/community");
    expect(community.match).toEqual(["/app/members", "/app/subgroups"]);
  });
  it("phone extra nav is Community, Wishlists and Inbox", () => {
    expect(PHONE_EXTRA_NAV.map((i) => i.label)).toEqual([
      "Community",
      "Wishlists",
      "Inbox",
    ]);
  });
  it("more nav is Settings, Admin; Inbox is top nav", () => {
    expect(MORE_NAV.map((i) => i.label)).toEqual([
      "Time capsules",
      "Recipes",
      "Settings",
      "Admin",
    ]);
    expect(find(TOP_NAV, "Inbox")).toMatchObject({
      href: "/app/inbox",
      match: ["/app/notifications", "/app/bookmarks", "/app/lists"],
    });
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
  it("isItemActive also honours match prefixes", () => {
    const community = find(TOP_NAV, "Community");
    expect(isItemActive("/app/members/123", community)).toBe(true);
    expect(isItemActive("/app/subgroups/choir", community)).toBe(true);
    expect(isItemActive("/app/community", community)).toBe(true);
    expect(isItemActive("/app/events", community)).toBe(false);
  });
  it("isItemActive honours Inbox match prefixes", () => {
    const inbox = find(TOP_NAV, "Inbox");
    expect(isItemActive("/app/bookmarks", inbox)).toBe(true);
    expect(isItemActive("/app/lists/x", inbox)).toBe(true);
    expect(isItemActive("/app/settings", inbox)).toBe(false);
  });
});

test("isAdmin is role-based", async () => {
  const { isAdmin } = await import("@/components/layout/navItems");
  expect(isAdmin({ role: "admin" })).toBe(true);
  expect(isAdmin({ role: "member" })).toBe(false);
  expect(isAdmin(null)).toBe(false);
});
