/**
 * @file tests/unit/settings/SettingsTabs.test.tsx
 * @brief SettingsTabs: PageHeader + side nav, active tab via ?tab=.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const nav = vi.hoisted(() => ({ tab: null as string | null }));
const plug = vi.hoisted(() => ({ on: false }));
vi.mock("@/hooks/usePluginUi", () => ({
  usePluginUi: () => ({
    data: plug.on
      ? [
          {
            plugin_id: "a",
            name: "A",
            composer_flags: {},
            user_prefs: { x: {} },
          },
        ]
      : [],
  }),
}));
vi.mock("@/components/settings/PluginPrefsTab", () => ({
  PluginPrefsTab: () => <p>body:plugins</p>,
}));
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: () => nav.tab }),
  useRouter: () => ({ push: vi.fn() }),
}));
const stub = vi.hoisted(() => (name: string) => () => <p>{`body:${name}`}</p>);
vi.mock("@/components/events/CalendarSubscriptionsPanel", () => ({
  CalendarSubscriptionsPanel: stub("calendar"),
}));
vi.mock("@/components/settings/AccountTab", () => ({
  AccountTab: stub("account"),
}));
vi.mock("@/components/settings/ProfileTab", () => ({
  ProfileTab: stub("profile"),
}));
vi.mock("@/components/settings/NotificationsTab", () => ({
  NotificationsTab: stub("notifications"),
}));
vi.mock("@/components/settings/PrivacyTab", () => ({
  PrivacyTab: stub("privacy"),
}));
vi.mock("@/components/settings/AppearanceTab", () => ({
  AppearanceTab: stub("appearance"),
}));
vi.mock("@/components/settings/NudgePreferences", () => ({
  NudgePreferences: stub("engagement"),
}));
vi.mock("@/components/settings/SecurityTab", () => ({
  SecurityTab: stub("security"),
}));
vi.mock("@/components/settings/StorageTab", () => ({
  StorageTab: stub("storage"),
}));

import { SettingsTabs } from "@/components/settings/SettingsTabs";

const IDS = [
  "account",
  "security",
  "profile",
  "notifications",
  "privacy",
  "appearance",
  "calendar",
  "engagement",
  "storage",
  "help",
];

describe("SettingsTabs", () => {
  beforeEach(() => {
    nav.tab = null;
  });

  it("renders the Settings header and a nav with 10 tab links (plugins hidden with none)", () => {
    render(<SettingsTabs />);
    expect(
      screen.getByRole("heading", { name: "Settings", level: 1 }),
    ).toBeTruthy();
    const links = screen
      .getByRole("navigation", { name: "Settings sections" })
      .querySelectorAll("a");
    expect([...links].map((a) => a.getAttribute("href"))).toEqual(
      IDS.map((i) => `?tab=${i}`),
    );
    expect(links[0].querySelector("svg")).not.toBeNull();
  });

  it("shows the Plugins tab when a plugin has member prefs", () => {
    plug.on = true;
    nav.tab = "plugins";
    render(<SettingsTabs />);
    plug.on = false;
    expect(screen.getByText("body:plugins")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^Plugins/ })).toBeTruthy();
  });

  it("defaults to the account tab", () => {
    render(<SettingsTabs />);
    expect(screen.getByText("body:account")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Account" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("shows the tab named by ?tab=", () => {
    nav.tab = "privacy";
    render(<SettingsTabs />);
    expect(screen.getByText("body:privacy")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Privacy" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Account" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("shows the Help tab for ?tab=help", () => {
    nav.tab = "help";
    render(<SettingsTabs />);
    expect(
      screen.getByRole("button", { name: "Keyboard shortcuts" }),
    ).toBeInTheDocument();
  });

  it("falls back to account for an unknown tab", () => {
    nav.tab = "nope";
    render(<SettingsTabs />);
    expect(screen.getByText("body:account")).toBeInTheDocument();
  });

  it("does not use bg-accent or its own max-width wrapper", () => {
    const { container } = render(<SettingsTabs />);
    expect(container.innerHTML).not.toMatch(/bg-accent|max-w-5xl/);
  });
});
