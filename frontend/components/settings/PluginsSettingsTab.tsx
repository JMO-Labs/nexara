"use client";
/**
 * @file components/settings/PluginsSettingsTab.tsx
 * @brief Plugins settings tab: empty state until plugins register sections.
 *        Phase 4 will inject plugin sections here via named slots.
 */
import { usePluginSettingsSections } from "@/lib/plugins/PluginSettingsContext";

/**
 * @brief Render registered plugin sections, or an empty state.
 * @return tab content
 */
export function PluginsSettingsTab() {
  const sections = usePluginSettingsSections();
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-bold">Plugins</h2>
      {sections.length === 0 ? (
        <div className="rounded-xl bg-surface p-4">
          <p className="text-sm">
            Plugin settings will appear here when plugins are installed.
          </p>
          <p className="mt-1 text-sm text-muted">
            Plugins extend Nexara with custom features. Install from Plugin
            Gallery.
          </p>
        </div>
      ) : (
        sections.map(({ pluginId, Component }) => (
          <section key={pluginId} aria-label={pluginId}>
            <Component />
          </section>
        ))
      )}
    </div>
  );
}
