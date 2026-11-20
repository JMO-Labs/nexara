/**
 * @file tests/unit/layout/AvatarMenu.test.tsx
 * @brief AvatarMenu items: profile link, admin gating, sign out.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const logout = vi.fn().mockResolvedValue(undefined);
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/lib/api/auth", () => ({
  logout: (...a: unknown[]) => logout(...a),
}));
vi.mock("@/lib/auth/session", () => ({ setAccessToken: vi.fn() }));

import { useSession } from "@/stores/session";
import { AvatarMenu } from "@/components/layout/AvatarMenu";

function setRole(role: string) {
  useSession.setState({
    user: { id: "u1", role, display_name: "Ann", email: "a@x.io" } as never,
    status: "authenticated",
  });
}

async function open() {
  render(<AvatarMenu />);
  await userEvent.click(screen.getByRole("button", { name: "Account menu" }));
}

describe("AvatarMenu", () => {
  beforeEach(() => logout.mockClear());

  it("hides Admin for members and links Profile", async () => {
    setRole("member");
    await open();
    expect(screen.getByRole("menuitem", { name: "Profile" })).toHaveAttribute(
      "href",
      "/app/members/u1",
    );
    expect(screen.getByRole("menuitem", { name: "Settings" })).toBeVisible();
    expect(screen.queryByRole("menuitem", { name: "Admin" })).toBeNull();
  });

  it("shows Admin for admins", async () => {
    setRole("admin");
    await open();
    expect(screen.getByRole("menuitem", { name: "Admin" })).toBeVisible();
  });

  it("Sign out calls logout", async () => {
    setRole("member");
    await open();
    await userEvent.click(screen.getByRole("menuitem", { name: "Sign out" }));
    expect(logout).toHaveBeenCalled();
  });
});
