"use client";
/**
 * @file components/settings/SettingsTabs.tsx
 * @brief Settings page: section nav + detail. Deep-linkable via ?tab=.
 *        Phone: list first, then detail with a back link. md+: side nav + detail.
 */
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
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

const TABS = [
  { id: "account", label: "Account", Panel: AccountTab },
  { id: "profile", label: "Profile", Panel: ProfileTab },
  { id: "notifications", label: "Notifications", Panel: NotificationsTab },
  { id: "privacy", label: "Privacy", Panel: PrivacyTab },
  { id: "appearance", label: "Appearance", Panel: AppearanceTab },
  { id: "calendar", label: "Calendar", Panel: CalendarSubscriptionsPanel },
  { id: "engagement", label: "Engagement", Panel: NudgePreferences },
  { id: "storage", label: "Storage", Panel: StorageTab },
  { id: "plugins", label: "Plugins", Panel: PluginsSettingsTab },
];

/**
 * @brief Settings sections with list-to-detail on phones.
 * @return settings layout
 */
export function SettingsTabs() {
  const param = useSearchParams().get("tab");
  const active = TABS.find((t) => t.id === param);
  const current = active ?? TABS[0];
  const Panel = current.Panel;

  return (
    <PluginSettingsProvider>
      <div className="mx-auto w-full max-w-5xl px-4 py-4 md:px-6 md:py-6">
        <header className="mb-4">
          <h1 className="text-3xl font-black">Settings</h1>
          <p className="text-sm text-muted">
            Manage your account preferences and settings.
          </p>
        </header>

        <div className="md:grid md:grid-cols-[14rem_1fr] md:gap-6">
          <nav
            aria-label="Settings sections"
            className={cn("md:block", active && "hidden")}
          >
            <ul className="flex flex-col gap-1">
              {TABS.map(({ id, label }) => (
                <li key={id}>
                  <Link
                    href={`?tab=${id}`}
                    replace
                    aria-current={current.id === id ? "page" : undefined}
                    className={cn(
                      "flex min-h-11 items-center justify-between rounded-xl px-3 text-sm font-semibold outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
                      "md:aria-[current=page]:bg-accent md:aria-[current=page]:text-surface-strong",
                      "bg-surface md:bg-transparent md:hover:bg-surface",
                    )}
                  >
                    {label}
                    <ChevronRight
                      aria-hidden="true"
                      className="size-4 md:hidden"
                    />
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <section
            aria-label={current.label}
            className={cn("min-w-0 md:block", !active && "hidden")}
          >
            <Link
              href="?"
              replace
              className="mb-3 inline-flex min-h-11 items-center gap-1 text-sm font-semibold md:hidden"
            >
              <ChevronLeft aria-hidden="true" className="size-4" />
              All settings
            </Link>
            <Panel />
          </section>
        </div>
      </div>
    </PluginSettingsProvider>
  );
}
