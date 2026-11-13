/**
 * @file lib/notifications/renderers.ts
 * @brief Notification renderers: default renderer + plugin registration.
 */
import type { NotificationTypeDescriptor } from "./types";

export type Translate = (key: string) => string;

export interface RenderedAction {
  key: string;
  label: string;
  method: "POST" | "PUT" | "DELETE";
  url: string;
  style: "primary" | "neutral" | "danger";
}

export interface RenderedNotif {
  title: string;
  body: string;
  icon: string;
  link: string | null;
  actions: RenderedAction[];
}

export type RenderFn = (
  type: NotificationTypeDescriptor,
  payload: Record<string, unknown>,
  t: Translate,
) => RenderedNotif;

const custom = new Map<string, RenderFn>();

/** @brief Register a custom renderer for a type key (plugins). */
export function registerRenderer(typeKey: string, fn: RenderFn): void {
  custom.set(typeKey, fn);
}

/** @brief Test helper: clear custom renderers. */
export function _resetRenderers(): void {
  custom.clear();
}

/** @brief Replace `{name}` placeholders from payload; unknown ones stay. */
export function _interpolate(
  template: string,
  payload: Record<string, unknown>,
): string {
  return template.replace(/\{(\w+)\}/g, (m, k: string) => {
    const v = payload[k];
    return v === undefined || v === null ? m : encodeURIComponent(String(v));
  });
}

const defaultRender: RenderFn = (type, payload, t) => ({
  title: t(type.label_i18n),
  body: typeof payload.message === "string" ? payload.message : "",
  icon: type.icon,
  link: typeof payload.link === "string" && payload.link ? payload.link : null,
  actions: type.actions.map((a) => ({
    key: a.key,
    label: t(a.label_i18n),
    method: a.method,
    url: _interpolate(a.url_template, payload),
    style: a.style,
  })),
});

/** @brief Render a notification via custom renderer or the default. */
export function renderNotif(
  type: NotificationTypeDescriptor,
  payload: Record<string, unknown>,
  t: Translate,
): RenderedNotif {
  return (custom.get(type.key) ?? defaultRender)(type, payload, t);
}
