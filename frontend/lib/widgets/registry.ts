/**
 * @file lib/widgets/registry.ts
 * @brief In-process widget registry. Widgets register themselves at module
 *        load time via side-effect imports; the registry never imports React
 *        components directly — that is the caller's concern.
 */

import type React from 'react';

export type WidgetSize = 'sm' | 'md' | 'lg' | 'full';
export type WidgetCategory = 'core' | 'social' | 'media' | 'plugin';

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
 * @param id        Unique stable key (e.g. 'feed', 'upcoming-events').
 * @param title     Human-readable name shown in the add menu and frame header.
 * @param description Optional blurb shown in the widget gallery.
 * @param defaultProps Default prop values merged at instantiation time.
 * @param defaultSize Initial column-span for new instances.
 * @param category  Grouping for the add-widget gallery.
 * @param Component React component rendered inside WidgetFrame.
 * @param permissions Optional guard; if returns false the widget is hidden.
 */
export interface WidgetDef<P = unknown> {
  id: string;
  title: string;
  description?: string;
  defaultProps?: P;
  defaultSize: WidgetSize;
  category: WidgetCategory;
  Component: React.ComponentType<WidgetContext<P>>;
  permissions?: (user: SessionUser) => boolean;
}

/**
 * @brief A persisted instance of a widget in the user's layout.
 *
 * @param id        UUIDv4 generated at creation time (instance id).
 * @param defId     References WidgetDef.id.
 * @param size      Current column-span override (may differ from defaultSize).
 * @param collapsed Whether the widget body is hidden.
 * @param order     Zero-based position in the layout grid.
 * @param props     Per-instance prop overrides (merged with WidgetDef.defaultProps).
 */
export interface WidgetInstance {
  id: string;
  defId: string;
  size: WidgetSize;
  collapsed: boolean;
  order: number;
  props?: unknown;
}

// ---------------------------------------------------------------------------
// Internal store
// ---------------------------------------------------------------------------

const _registry = new Map<string, WidgetDef>();

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * @brief Register a widget definition.
 *
 * @param def The WidgetDef to register.
 * @throws Error if a definition with the same id is already registered.
 */
export function register(def: WidgetDef): void {
  if (_registry.has(def.id)) {
    throw new Error(`Widget '${def.id}' is already registered.`);
  }
  _registry.set(def.id, def);
}

/**
 * @brief Look up a widget definition by id.
 *
 * @param id The widget definition id.
 * @return The WidgetDef, or undefined if not found.
 */
export function getDef(id: string): WidgetDef | undefined {
  return _registry.get(id);
}

/**
 * @brief List all registered widget definitions, sorted by category then title.
 *
 * @return Sorted array of WidgetDef.
 */
export function listDefs(): WidgetDef[] {
  return Array.from(_registry.values()).sort((a, b) => {
    if (a.category !== b.category) return a.category.localeCompare(b.category);
    return a.title.localeCompare(b.title);
  });
}

/**
 * @brief Clear all registrations. Intended for testing only.
 */
export function clearRegistry(): void {
  _registry.clear();
}
