/**
 * @file tests/unit/settings/SettingsPage.test.tsx
 * @brief Settings tabs: Plugins tab and plugin settings registry.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";

let tab: string | null = "plugins";
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: () => tab }),
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
import {
  PluginSettingsProvider,
  useRegisterPluginSettings,
  usePluginSettings,
  usePluginSettingsSections,
} from "@/lib/plugins/PluginSettingsContext";

describe("Settings Plugins tab", () => {
  it("lists Plugins in the nav", () => {
    render(<SettingsTabs />);
    expect(screen.getByRole("link", { name: /^Plugins/ })).toBeTruthy();
  });

  it("renders the empty state", () => {
    render(<SettingsTabs />);
    expect(
      screen.getByRole("heading", { name: "Plugins", level: 2 }),
    ).toBeTruthy();
    expect(
      screen.getByText(
        "Plugin settings will appear here when plugins are installed.",
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(
        "Plugins extend Nexara with custom features. Install from Plugin Gallery.",
      ),
    ).toBeTruthy();
  });
});

describe("PluginSettingsContext", () => {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <PluginSettingsProvider>{children}</PluginSettingsProvider>
  );

  it("registers and unregisters sections without conflicts", () => {
    const A = () => <div>A</div>;
    const B = () => <div>B</div>;
    const { result, unmount } = renderHook(
      () => {
        useRegisterPluginSettings("a", A);
        useRegisterPluginSettings("b", B);
        return usePluginSettingsSections();
      },
      { wrapper },
    );
    expect(result.current.map((s) => s.pluginId).sort()).toEqual(["a", "b"]);
    unmount();
  });

  it("reads and writes per-plugin settings", () => {
    const { result } = renderHook(() => usePluginSettings("a"), { wrapper });
    expect(result.current.settings).toEqual({});
    act(() => result.current.update({ x: 1 }));
    expect(result.current.settings).toEqual({ x: 1 });
  });
});
