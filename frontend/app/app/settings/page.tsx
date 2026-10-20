/**
 * @file app/app/settings/page.tsx
 * @brief Settings page: server component shell that mounts SettingsTabs client component.
 */
import { SettingsTabs } from "@/components/settings/SettingsTabs";

/**
 * @brief Render the settings page.
 * @return Server component wrapping the client SettingsTabs component.
 */
export default function SettingsPage() {
  return <SettingsTabs />;
}
