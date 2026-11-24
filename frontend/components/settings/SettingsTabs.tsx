"use client";
/**
 * @file components/settings/SettingsTabs.tsx
 * @brief Settings page: PageHeader + TwoPane (SideNav | active section).
 *        Phone shows a section picker instead of the clipped side nav.
 *        Deep-linkable via ?tab=.
 */
import { useRouter, useSearchParams } from "next/navigation";
import {
  Bell,
  CalendarDays,
  CircleHelp,
  HardDrive,
  Heart,
  KeyRound,
  Lock,
  Palette,
  Puzzle,
  ShieldCheck,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import { Option, Select } from "@/components/ui/Select";
import { PageHeader, SideNav, TwoPane } from "@/components/ui/page";
import { CalendarSubscriptionsPanel } from "@/components/events/CalendarSubscriptionsPanel";
import { AccountTab } from "./AccountTab";
import { ProfileTab } from "./ProfileTab";
import { NotificationsTab } from "./NotificationsTab";
import { AppearanceTab } from "./AppearanceTab";
import { PrivacyTab } from "./PrivacyTab";
import { StorageTab } from "./StorageTab";
import { NudgePreferences } from "./NudgePreferences";
import { PluginsComingSoon } from "@/components/admin/PluginsComingSoon";
import { HelpTab } from "./HelpTab";
import { SecurityTab } from "./SecurityTab";

const TABS: {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
  Body: () => React.JSX.Element | null;
}[] = [
  {
    id: "account",
    label: "Account",
    description: "Your sign-in email and data.",
    icon: KeyRound,
    Body: AccountTab,
  },
  {
    id: "security",
    label: "Security",
    description: "Two-step sign-in, recovery codes and passkeys.",
    icon: ShieldCheck,
    Body: SecurityTab,
  },
  {
    id: "profile",
    label: "Profile",
    description: "How you appear to other members.",
    icon: UserRound,
    Body: ProfileTab,
  },
  {
    id: "notifications",
    label: "Notifications",
    description: "Choose what reaches you, when and where.",
    icon: Bell,
    Body: NotificationsTab,
  },
  {
    id: "privacy",
    label: "Privacy",
    description: "Control who can see your profile and activity.",
    icon: Lock,
    Body: PrivacyTab,
  },
  {
    id: "appearance",
    label: "Appearance",
    description: "Theme, text size and background.",
    icon: Palette,
    Body: AppearanceTab,
  },
  {
    id: "calendar",
    label: "Calendar",
    description: "Subscribe to external calendars.",
    icon: CalendarDays,
    Body: CalendarSubscriptionsPanel,
  },
  {
    id: "engagement",
    label: "Engagement",
    description: "Nudges and reminders to stay involved.",
    icon: Heart,
    Body: NudgePreferences,
  },
  {
    id: "storage",
    label: "Storage",
    description: "How much media space you are using.",
    icon: HardDrive,
    Body: StorageTab,
  },
  {
    id: "plugins",
    label: "Plugins",
    description: "Plugins for your community.",
    icon: Puzzle,
    Body: PluginsComingSoon,
  },
  {
    id: "help",
    label: "Help",
    description: "Keyboard shortcuts and quick help.",
    icon: CircleHelp,
    Body: HelpTab,
  },
];

const ITEMS = TABS.map(({ id, label, icon }) => ({
  id,
  label,
  icon,
  href: `?tab=${id}`,
}));

/**
 * @brief Settings sections beside a glass side nav (phone: a picker).
 * @return settings layout
 */
export function SettingsTabs() {
  const param = useSearchParams().get("tab");
  const router = useRouter();
  const current = TABS.find((t) => t.id === param) ?? TABS[0];
  const Body = current.Body;

  return (
    <>
      <PageHeader title="Settings" description={current.description} />
      <TwoPane
        aside={
          <>
            <div className="md:hidden">
              <Select
                label="Settings sections"
                value={current.id}
                onValueChange={(v) => router.push(`?tab=${v}`)}
              >
                {TABS.map((t) => (
                  <Option key={t.id} value={t.id}>
                    {t.label}
                  </Option>
                ))}
              </Select>
            </div>
            <div className="hidden md:block">
              <SideNav
                items={ITEMS}
                activeId={current.id}
                label="Settings sections"
              />
            </div>
          </>
        }
        asideWidth={240}
      >
        <section aria-label={current.label} className="flex flex-col gap-4">
          <Body />
        </section>
      </TwoPane>
    </>
  );
}
