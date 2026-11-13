/**
 * @file tests/unit/layout/MoreSheet.test.tsx
 * @brief MoreSheet open/close, nav links and admin gating.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../utils/renderWithProviders";

vi.mock("next/navigation", () => ({
  usePathname: () => "/app",
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/lib/api/auth", () => ({
  logout: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("@/lib/auth/session", () => ({ setAccessToken: vi.fn() }));

import { useSession } from "@/stores/session";
import { MoreSheet } from "@/components/layout/MoreSheet";

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

  it("opens and lists nav links", () => {
    renderWithProviders(<MoreSheet open onClose={vi.fn()} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Galleries" })).toHaveAttribute(
      "href",
      "/app/galleries",
    );
    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Admin" })).toBeNull();
    expect(
      screen.getByRole("button", { name: /sign out/i }),
    ).toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    const onClose = vi.fn();
    renderWithProviders(<MoreSheet open onClose={onClose} />);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
