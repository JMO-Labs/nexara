/**
 * @file app/app/admin/plugins/page.tsx
 * @brief Plugin browser (admin role required).
 */
import { PluginsAdmin } from "@/components/admin/PluginsAdmin";

export const metadata = { title: "Plugins" };

export default function PluginsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-black">Plugins</h1>
        <p className="text-sm text-muted">
          Install, configure and manage plugins.
        </p>
      </div>
      <PluginsAdmin />
    </div>
  );
}
