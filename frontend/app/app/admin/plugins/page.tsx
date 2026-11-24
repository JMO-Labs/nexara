/**
 * @file app/app/admin/plugins/page.tsx
 * @brief Installed plugins (frame and admin gate in admin/layout.tsx).
 */
import { InstalledTab } from "@/components/admin/plugins/InstalledTab";

export const metadata = { title: "Plugins" };

export default function PluginsPage() {
  return <InstalledTab />;
}
