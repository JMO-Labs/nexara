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
vi.mock("@/components/layout/AvatarMenu", () => ({
  AvatarMenu: () => <button aria-label="Account menu" />,
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
