"use client";
/**
 * @file components/settings/SettingsTabs.tsx
 * @brief Settings page: PageHeader + TwoPane (SideNav | active section).
 *        Deep-linkable via ?tab=.
 */
import { useSearchParams } from "next/navigation";
import {
  Bell,
  CalendarDays,
  HardDrive,
  Heart,
  Lock,
  Palette,
  Puzzle,
  User,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import { PageHeader, SideNav, TwoPane } from "@/components/ui/page";
import { CalendarSubscriptionsPanel } from "@/components/events/CalendarSubscriptionsPanel";
import { AccountTab } from "./AccountTab";
import { ProfileTab } from "./ProfileTab";
import { NotificationsTab } from "./NotificationsTab";
import { AppearanceTab } from "./AppearanceTab";
import { PrivacyTab } from "./PrivacyTab";
import { StorageTab } from "./StorageTab";
import { NudgePreferences } from "./NudgePreferences";
import { PluginsSettingsTab } from "./PluginsSettingsTab";
import { PluginSettingsProvider } from "@/lib/plugins/PluginSettingsContext";

const TABS: {
  id: string;
  label: string;
  icon: LucideIcon;
  Body: () => React.JSX.Element | null;
}[] = [
  { id: "account", label: "Account", icon: User, Body: AccountTab },
  { id: "profile", label: "Profile", icon: UserRound, Body: ProfileTab },
  {
    id: "notifications",
    label: "Notifications",
    icon: Bell,
    Body: NotificationsTab,
  },
  { id: "privacy", label: "Privacy", icon: Lock, Body: PrivacyTab },
  { id: "appearance", label: "Appearance", icon: Palette, Body: AppearanceTab },
  {
    id: "calendar",
    label: "Calendar",
    icon: CalendarDays,
    Body: CalendarSubscriptionsPanel,
  },
  {
    id: "engagement",
    label: "Engagement",
    icon: Heart,
    Body: NudgePreferences,
  },
  { id: "storage", label: "Storage", icon: HardDrive, Body: StorageTab },
  { id: "plugins", label: "Plugins", icon: Puzzle, Body: PluginsSettingsTab },
];

const ITEMS = TABS.map(({ id, label, icon }) => ({
  id,
  label,
  icon,
  href: `?tab=${id}`,
}));

/**
 * @brief Settings sections beside a glass side nav.
 * @return settings layout
 */
export function SettingsTabs() {
  const param = useSearchParams().get("tab");
  const current = TABS.find((t) => t.id === param) ?? TABS[0];
  const Body = current.Body;

  return (
    <PluginSettingsProvider>
      <PageHeader
        title="Settings"
        description="Manage your account preferences and settings."
      />
      <TwoPane
        aside={
          <SideNav
            items={ITEMS}
            activeId={current.id}
            label="Settings sections"
          />
        }
        asideWidth={240}
      >
        <section aria-label={current.label} className="flex flex-col gap-4">
          <Body />
        </section>
      </TwoPane>
    </PluginSettingsProvider>
  );
}
