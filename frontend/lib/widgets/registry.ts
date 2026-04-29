/**
 * @file lib/widgets/registry.ts
 * @brief In-process widget registry. Widgets register themselves at module
 *        load time; the registry never imports React components directly.
 *        Layout positions are stored as react-grid-layout (x, y, w, h).
 */

import type React from "react";

/** Total columns in the dashboard grid. Matches react-grid-layout default. */
export const GRID_COLS = 12;

/** Default row height in pixels for react-grid-layout. */
export const GRID_ROW_HEIGHT = 80;

export type WidgetCategory = "core" | "social" | "media" | "plugin";

/** @brief Minimal session user shape needed for permission checks. */
export interface SessionUser {
  id: string;
  community_id?: string;
  [key: string]: unknown;
}

/** @brief Runtime context passed to every widget component as props. */
export interface WidgetContext<P = unknown> {
  instanceId: string;
  props?: P;
}

/**
 * @brief Static definition of a widget type.
 *
 * @param defaultSize Initial width in grid columns (1..12) for new instances.
 * @param defaultH    Initial height in grid rows for new instances.
 * @param minW/minH   Lower bound of the resize handle.
 */
export interface WidgetDef<P = unknown> {
  id: string;
  title: string;
  description?: string;
  defaultProps?: P;
  defaultSize: number;
  defaultH?: number;
  minW?: number;
  minH?: number;
  category: WidgetCategory;
  Component: React.ComponentType<WidgetContext<P>>;
  permissions?: (user: SessionUser) => boolean;
}

/**
 * @brief A persisted widget instance with grid coordinates.
 */
export interface WidgetInstance {
  id: string;
  defId: string;
  x: number;
  y: number;
  w: number;
  h: number;
  collapsed: boolean;
  props?: Record<string, unknown>;
}

const _registry = new Map<string, WidgetDef>();

export function register(def: WidgetDef): void {
  const existing = _registry.get(def.id);
  if (existing !== undefined) {
    if (existing.Component === def.Component) return;
    console.warn(
      `Widget '${def.id}' re-registered with a different Component. Overwriting.`,
    );
  }
  _registry.set(def.id, def);
}

export function getDef(id: string): WidgetDef | undefined {
  return _registry.get(id);
}

export function listDefs(): WidgetDef[] {
  return Array.from(_registry.values()).sort((a, b) => {
    if (a.category !== b.category) return a.category.localeCompare(b.category);
    return a.title.localeCompare(b.title);
  });
}

export function clearRegistry(): void {
  _registry.clear();
}
