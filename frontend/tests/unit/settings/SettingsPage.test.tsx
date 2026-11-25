/**
 * @file tests/unit/settings/SettingsPage.test.tsx
 * @brief Settings tabs: Plugins tab visibility.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const tab: string | null = "plugins";
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: () => tab }),
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/components/events/CalendarSubscriptionsPanel", () => ({
  CalendarSubscriptionsPanel: () => null,
}));
vi.mock("@/components/settings/AccountTab", () => ({ AccountTab: () => null }));
vi.mock("@/components/settings/ProfileTab", () => ({ ProfileTab: () => null }));
vi.mock("@/components/settings/NotificationsTab", () => ({
  NotificationsTab: () => null,
}));
vi.mock("@/components/settings/AppearanceTab", () => ({
  AppearanceTab: () => null,
}));
vi.mock("@/components/settings/StorageTab", () => ({ StorageTab: () => null }));

import { SettingsTabs } from "@/components/settings/SettingsTabs";

describe("Settings Plugins tab", () => {
  it("is hidden when no plugin has member prefs", () => {
    render(<SettingsTabs />);
    expect(screen.queryByRole("link", { name: /^Plugins/ })).toBeNull();
  });
});
