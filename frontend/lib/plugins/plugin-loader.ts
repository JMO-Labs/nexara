/**
 * @file lib/plugins/plugin-loader.ts
 * @brief Plugin discovery and slot registry (singleton).
 */
import type { ComponentType } from "react";
import { apiGet } from "@/lib/api/client";

/** @brief Plugin summary as returned by GET /plugins. */
export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  is_enabled: boolean;
  description: string;
}

/** @brief Props every slot component receives. */
export interface PluginComponentProps {
  pluginId: string;
  pluginManifest: PluginManifest;
}

export type SlotName =
  | "sidebar-widget"
  | "profile-tab"
  | "settings-section"
  | "post-action"
  | "admin-tab";

export interface SlotEntry {
  pluginId: string;
  component: ComponentType<PluginComponentProps>;
}

/** @brief Stores plugin slot components. Use getInstance(). */
export class PluginRegistry {
  private static instance: PluginRegistry | null = null;
  private slots = new Map<string, SlotEntry[]>();
  private manifests = new Map<string, PluginManifest>();
  private listeners = new Set<() => void>();
  private version = 0;

  static getInstance(): PluginRegistry {
    return (PluginRegistry.instance ??= new PluginRegistry());
  }

  /** @brief Map a component to a named slot for a plugin. */
  registerSlotComponent(
    slotName: string,
    pluginId: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- plugins declare arbitrary slot props
    component: ComponentType<any>,
  ): void {
    const list = this.slots.get(slotName) ?? [];
    if (list.some((e) => e.pluginId === pluginId && e.component === component))
      return;
    this.slots.set(slotName, [...list, { pluginId, component }]);
    this.emit();
  }

  /** @brief Entries registered for a slot (stable between changes). */
  getSlotComponents(slotName: string): SlotEntry[] {
    return this.slots.get(slotName) ?? EMPTY;
  }

  setManifest(m: PluginManifest): void {
    this.manifests.set(m.id, m);
  }

  getManifest(id: string): PluginManifest | undefined {
    return this.manifests.get(id);
  }

  subscribe = (fn: () => void): (() => void) => {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  };

  getVersion = (): number => this.version;

  /** @brief Clear all state (tests). */
  reset(): void {
    this.slots.clear();
    this.manifests.clear();
    this.emit();
  }

  private emit(): void {
    this.version++;
    this.listeners.forEach((l) => l());
  }
}

const EMPTY: SlotEntry[] = [];

export type PluginImporter = (
  pluginId: string,
) => Promise<{ registerPlugin?: (r: PluginRegistry) => void }>;

/** @brief Fetch installed plugins. */
export function fetchPluginManifests(): Promise<PluginManifest[]> {
  return apiGet<PluginManifest[]>("/plugins");
}

// Template-literal import lets the bundler code-split every plugins/<id>.
const defaultImporter: PluginImporter = (id) =>
  import(`@/plugins/${id.replace(/[^a-z0-9_-]/gi, "")}/index`);

/** @brief Fetch manifests, import enabled plugins, call registerPlugin. */
export async function loadPlugins(
  importer: PluginImporter = defaultImporter,
): Promise<void> {
  let manifests: PluginManifest[];
  try {
    manifests = await fetchPluginManifests();
  } catch (err) {
    console.error("plugins: manifest fetch failed", err);
    return;
  }
  const registry = PluginRegistry.getInstance();
  for (const m of manifests.filter((p) => p.is_enabled)) {
    try {
      const mod = await importer(m.id);
      if (typeof mod.registerPlugin !== "function")
        throw new Error("missing registerPlugin export");
      registry.setManifest(m);
      mod.registerPlugin(registry);
    } catch (err) {
      console.error(`plugins: failed to load "${m.id}"`, err);
    }
  }
}
