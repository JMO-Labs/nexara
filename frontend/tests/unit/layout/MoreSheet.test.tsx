/**
 * @file tests/unit/layout/MoreSheet.test.tsx
 * @brief MoreSheet: open state, nav links, Escape to close.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/lib/api/auth", () => ({
  logout: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("@/lib/auth/session", () => ({ setAccessToken: vi.fn() }));

import { useSession } from "@/stores/session";
import { MoreSheet } from "@/components/layout/MoreSheet";
import { renderWithProviders } from "../../utils/renderWithProviders";

describe("MoreSheet", () => {
  beforeEach(() => {
    useSession.setState({
      user: { role: "member" } as never,
      status: "authenticated",
    });
  });

  it("renders nothing when closed", () => {
    renderWithProviders(<MoreSheet open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens and lists nav links plus sign out", () => {
    renderWithProviders(<MoreSheet open onClose={vi.fn()} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    for (const n of ["Galleries", "Media", "Members", "Settings", "Help"])
      expect(screen.getByRole("link", { name: n })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Admin" })).toBeNull();
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    const onClose = vi.fn();
    renderWithProviders(<MoreSheet open onClose={onClose} />);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
