/**
 * @file tests/unit/settings/PrivacyTab.test.tsx
 * @brief PrivacyTab tests: controls render current values and Save sends changes.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PrivacyTab } from "@/components/settings/PrivacyTab";
import * as hooks from "@/hooks/useSettings";

vi.mock("@/hooks/useSettings");

const settings = {
  theme: "system",
  locale: "en-US",
  profile_visible_to: "community",
  show_online_status: true,
  show_last_seen: false,
  show_birthday_to: "community",
  show_birthday_year: false,
  allow_sassybot: true,
  font_size: "medium",
  compact_feed: false,
};

describe("PrivacyTab", () => {
  const mutate = vi.fn();
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(hooks.useUserSettings).mockReturnValue({
      data: settings,
    } as any);
    vi.mocked(hooks.useUpdateSettings).mockReturnValue({
      mutate,
      isPending: false,
    } as any);
  });

  it("renders all privacy controls with current values", () => {
    render(<PrivacyTab />);
    expect(screen.getByLabelText("Profile visible to")).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: "Show online status" }),
    ).toBeChecked();
    expect(
      screen.getByRole("switch", { name: "Show last seen" }),
    ).not.toBeChecked();
    expect(screen.getByLabelText("Show birthday to")).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: "Show birthday year" }),
    ).not.toBeChecked();
    expect(
      screen.getByRole("switch", { name: "Allow Sassybot" }),
    ).toBeChecked();
  });

  it("disables Save until something changes, then sends only the diff", async () => {
    const user = userEvent.setup();
    render(<PrivacyTab />);
    const save = screen.getByRole("button", { name: "Save" });
    expect(save).toBeDisabled();
    await user.click(screen.getByRole("switch", { name: "Show last seen" }));
    expect(save).toBeEnabled();
    await user.click(save);
    expect(mutate).toHaveBeenCalledWith(
      { show_last_seen: true },
      expect.anything(),
    );
  });
});
