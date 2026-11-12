# Plugin settings (Phase 4 extension points)

Phase 3 ships the foundation only; no plugin integration yet.

## Frontend

- `Settings > Plugins` tab: `frontend/components/settings/PluginsSettingsTab.tsx`
  shows an empty state until a plugin registers a section.
- `frontend/lib/plugins/PluginSettingsContext.tsx`:
  - `PluginSettingsProvider` wraps the settings page.
  - `useRegisterPluginSettings(pluginId, Component)` registers a section
    (replaces a prior registration with the same id; unregisters on unmount).
  - `usePluginSettings(pluginId)` returns `{ settings, update(patch) }`,
    currently in memory.
  - `usePluginSettingsSections()` lists registered sections.

## Phase 4 work

- Wire plugin manifests to inject components via named slots.
- Expected manifest fields: `plugin_id`, `settings_sections[]` with `title`,
  `description`, `component` (path).
- Optional persistence: `plugin_settings` table
  (`user_id`, `plugin_id`, `settings JSONB`, scoped by `community_id`) plus CRUD
  endpoints; back `usePluginSettings` with them.
