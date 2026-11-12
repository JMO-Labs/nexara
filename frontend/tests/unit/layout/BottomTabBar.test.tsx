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

import { useSession } from "@/stores/session";
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

  it("renders 4 primary links and a More button", () => {
    render(<BottomTabBar />);
    for (const n of ["Home", "Chat", "Calendar", "Groups"])
      expect(screen.getByRole("link", { name: n })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Chat" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("button", { name: "More" })).toBeInTheDocument();
    expect(TAB_BAR_CLEARANCE).toContain("safe-area-inset-bottom");
  });

  it("opens More dialog with overflow items, no Admin for non-admin", async () => {
    render(<BottomTabBar />);
    await userEvent.click(screen.getByRole("button", { name: "More" }));
    const dlg = screen.getByRole("dialog", { name: "More" });
    for (const n of [
      "Galleries",
      "Media",
      "Members",
      "Notifications",
      "Settings",
      "Help",
    ])
      expect(dlg).toContainElement(screen.getByRole("link", { name: n }));
    expect(screen.queryByRole("link", { name: "Admin" })).toBeNull();
  });

  it("shows Admin for admins", async () => {
    setAdmin(true);
    render(<BottomTabBar />);
    await userEvent.click(screen.getByRole("button", { name: "More" }));
    expect(screen.getByRole("link", { name: "Admin" })).toBeInTheDocument();
  });

  it("Sign out calls logout", async () => {
    render(<BottomTabBar />);
    await userEvent.click(screen.getByRole("button", { name: "More" }));
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(logout).toHaveBeenCalled();
  });

  it("Escape closes the sheet", async () => {
    render(<BottomTabBar />);
    await userEvent.click(screen.getByRole("button", { name: "More" }));
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
