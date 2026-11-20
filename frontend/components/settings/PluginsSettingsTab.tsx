"use client";
/**
 * @file components/settings/PluginsSettingsTab.tsx
 * @brief Plugins settings tab: empty state until plugins register sections.
 *        Phase 4 will inject plugin sections here via named slots.
 */
import Link from "next/link";
import { Puzzle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/page";
import { usePluginSettingsSections } from "@/lib/plugins/PluginSettingsContext";

/**
 * @brief Render registered plugin sections, or an empty state.
 * @return tab content
 */
export function PluginsSettingsTab() {
  const sections = usePluginSettingsSections();
  if (sections.length === 0) {
    return (
      <Panel>
        <EmptyState
          icon={Puzzle}
          compact
          title="No plugins installed"
          description="Plugins extend Nexara with custom features."
          action={
            <Button asChild>
              <Link href="/app/admin/plugins">Browse plugins</Link>
            </Button>
          }
        />
      </Panel>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-bold">Plugins</h2>
      {sections.map(({ pluginId, Component }) => (
        <section key={pluginId} aria-label={pluginId}>
          <Component />
        </section>
      ))}
    </div>
  );
}
