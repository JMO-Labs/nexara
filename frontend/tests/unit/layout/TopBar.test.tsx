/**
 * @file tests/unit/layout/TopBar.test.tsx
 * @brief TopBar search button and bell.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/components/notifications/NotificationsBell", () => ({
  NotificationsBell: () => <button aria-label="Notifications" />,
}));
vi.mock("@/components/notifications/NotificationsDrawer", () => ({
  NotificationsDrawer: () => null,
}));
vi.mock("@/components/layout/AvatarMenu", () => ({
  AvatarMenu: () => <button aria-label="Account menu" />,
}));

vi.mock("@/components/layout/TopNav", () => ({
  TopNav: () => <nav aria-label="Main" />,
}));
vi.mock("@/components/layout/CreateMenu", () => ({
  CreateMenu: () => <button aria-label="Create" />,
}));
vi.mock("@/components/layout/MoreSheet", () => ({
  MoreSheet: ({ open }: { open: boolean }) =>
    open ? <div role="dialog" aria-label="More" /> : null,
}));
vi.mock("@/components/trips/ActiveTripBar", () => ({
  ActiveTripBar: () => null,
}));
vi.mock("@/hooks/useSettings", () => ({
  useUserSettings: () => ({ data: undefined }),
}));

import { TopBar } from "@/components/layout/TopBar";
import { useUI } from "@/stores/ui";

describe("TopBar", () => {
  it("opens the command palette from Search", async () => {
    const spy = vi.fn();
    useUI.setState({ setCommandPaletteOpen: spy } as never);
    render(<TopBar />);
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(spy).toHaveBeenCalledWith(true);
  });

  it("renders the bell", () => {
    render(<TopBar />);
    expect(
      screen.getByRole("button", { name: "Notifications" }),
    ).toBeInTheDocument();
  });
});

describe("TopBar nav", () => {
  it("renders the main nav and create menu", () => {
    render(<TopBar />);
    expect(
      screen.getByRole("navigation", { name: "Main" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Create" })).toHaveLength(2);
  });

  it("phone avatar button opens the More sheet", async () => {
    render(<TopBar />);
    await userEvent.click(screen.getByRole("button", { name: "More" }));
    expect(screen.getByRole("dialog", { name: "More" })).toBeInTheDocument();
  });
});
