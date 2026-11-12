"use client";
/**
 * @file lib/plugins/PluginSettingsContext.tsx
 * @brief Registry for plugin settings sections (Phase 4 extension point).
 *
 * Phase 4 will wire plugin manifests (`plugin_id`, `settings_sections` with
 * title, description, component path) to inject components here via named
 * slots. Until then nothing registers and the Plugins tab shows its empty
 * state. Sections are keyed by pluginId so plugins never conflict.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ComponentType,
  type ReactNode,
} from "react";

/** @brief A registered settings section. */
export interface PluginSettingsSection {
  pluginId: string;
  Component: ComponentType;
}

type Values = Record<string, unknown>;

interface Ctx {
  sections: PluginSettingsSection[];
  register: (s: PluginSettingsSection) => () => void;
  values: Record<string, Values>;
  update: (pluginId: string, patch: Values) => void;
}

const PluginSettingsCtx = createContext<Ctx | null>(null);

/**
 * @brief Provide the plugin settings registry. Values are in-memory only;
 *        Phase 4 persists them via a plugin_settings table and API.
 * @param children subtree
 * @return provider element
 */
export function PluginSettingsProvider({ children }: { children: ReactNode }) {
  const [sections, setSections] = useState<PluginSettingsSection[]>([]);
  const [values, setValues] = useState<Record<string, Values>>({});

  const register = useCallback((s: PluginSettingsSection) => {
    setSections((prev) => [
      ...prev.filter((p) => p.pluginId !== s.pluginId),
      s,
    ]);
    return () =>
      setSections((prev) =>
        prev.filter(
          (p) => !(p.pluginId === s.pluginId && p.Component === s.Component),
        ),
      );
  }, []);

  const update = useCallback((pluginId: string, patch: Values) => {
    setValues((prev) => ({
      ...prev,
      [pluginId]: { ...prev[pluginId], ...patch },
    }));
  }, []);

  const value = useMemo(
    () => ({ sections, register, values, update }),
    [sections, register, values, update],
  );
  return (
    <PluginSettingsCtx.Provider value={value}>
      {children}
    </PluginSettingsCtx.Provider>
  );
}

function useCtx(): Ctx {
  const c = useContext(PluginSettingsCtx);
  if (!c) throw new Error("PluginSettingsProvider missing");
  return c;
}

/**
 * @brief Register a settings component for a plugin; unregisters on unmount.
 * @param pluginId unique plugin id
 * @param Component settings section component
 */
export function useRegisterPluginSettings(
  pluginId: string,
  Component: ComponentType,
): void {
  const { register } = useCtx();
  useEffect(
    () => register({ pluginId, Component }),
    [register, pluginId, Component],
  );
}

/**
 * @brief Read/write one plugin's settings.
 * @param pluginId plugin id
 * @return current settings and an update(patch) merge function
 */
export function usePluginSettings(pluginId: string) {
  const { values, update } = useCtx();
  const settings = values[pluginId] ?? {};
  const set = useCallback(
    (patch: Values) => update(pluginId, patch),
    [update, pluginId],
  );
  return { settings, update: set };
}

/**
 * @brief All registered sections (empty until Phase 4).
 * @return sections list
 */
export function usePluginSettingsSections(): PluginSettingsSection[] {
  return useCtx().sections;
}
