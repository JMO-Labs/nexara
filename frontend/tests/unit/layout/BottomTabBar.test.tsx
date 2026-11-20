/**
 * @file tests/unit/layout/BottomTabBar.test.tsx
 * @brief Phone tab bar and More sheet.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const logout = vi.fn().mockResolvedValue(undefined);
vi.mock("next/navigation", () => ({
  usePathname: () => "/app/chat",
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/lib/api/auth", () => ({
  logout: (...a: unknown[]) => logout(...a),
}));
vi.mock("@/lib/auth/session", () => ({ setAccessToken: vi.fn() }));
const unread = vi.hoisted(() => ({
  value: { a: 1, b: 2 } as Record<string, number>,
}));
vi.mock("@/hooks/useChat", () => ({
  useChatRealtime: () => ({ unread: unread.value }),
}));

import { useSession } from "@/stores/session";
import { MoreSheet } from "@/components/layout/MoreSheet";
import {
  BottomTabBar,
  TAB_BAR_CLEARANCE,
} from "@/components/layout/BottomTabBar";

function setAdmin(isAdmin: boolean) {
  useSession.setState({
    user: { role: isAdmin ? "admin" : "member" } as never,
    status: "authenticated",
  });
}

describe("BottomTabBar", () => {
  beforeEach(() => {
    logout.mockClear();
    setAdmin(false);
  });

  it("renders 5 items with a Chat unread badge", () => {
    render(<BottomTabBar />);
    for (const n of ["Home", "Calendar", "Photos"])
      expect(screen.getByRole("link", { name: n })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^Chat/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Photos" })).toHaveAttribute(
      "href",
      "/app/photos",
    );
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a, button")).toHaveLength(5);
    expect(TAB_BAR_CLEARANCE).toContain("safe-area-inset-bottom");
  });

  it("MoreSheet lists overflow items, no Admin for non-admin", () => {
    render(<MoreSheet open onClose={() => {}} />);
    const dlg = screen.getByRole("dialog", { name: "More" });
    for (const n of ["Community", "Inbox", "Settings"])
      expect(dlg).toContainElement(screen.getByRole("link", { name: n }));
    expect(screen.queryByRole("button", { name: "Help" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Admin" })).toBeNull();
  });

  it("MoreSheet shows Admin for admins", () => {
    setAdmin(true);
    render(<MoreSheet open onClose={() => {}} />);
    expect(screen.getByRole("link", { name: "Admin" })).toBeInTheDocument();
  });

  it("MoreSheet Sign out calls logout", async () => {
    render(<MoreSheet open onClose={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(logout).toHaveBeenCalled();
  });
});
