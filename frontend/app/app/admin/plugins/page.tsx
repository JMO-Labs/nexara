/**
 * @file app/app/admin/plugins/page.tsx
 * @brief Plugin browser (frame and admin gate in admin/layout.tsx).
 */
import { PluginsAdmin } from "@/components/admin/PluginsAdmin";

export const metadata = { title: "Plugins" };

export default function PluginsPage() {
  return <PluginsAdmin />;
}
