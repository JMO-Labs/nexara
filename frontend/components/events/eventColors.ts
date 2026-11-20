/**
 * @file components/events/eventColors.ts
 * @brief Color assignment for events. Colours come from lib/groupColor so a
 *        group renders the same hue on the calendar, rail dots and detail
 *        panel; an explicit event colour overrides. Text is always ink.
 */
import type { EventItem } from "@/lib/api/events";
import { groupColor } from "@/lib/groupColor";

export interface EventTone {
  /** Solid bar / dot / accent color. */
  solid: string;
  /** Translucent fill for soft surfaces. */
  soft: string;
  /** Foreground for text on `solid`. */
  onSolid: string;
  /** Foreground for text on `soft`. */
  onSoft: string;
  /** Short label, e.g. "Community" or subgroup name (caller may override). */
  label: string;
}

const INK = "var(--nx-ink)";

/**
 * @brief Build a tone from a single group/event colour.
 * @param color CSS colour (hex or var())
 * @param label short label
 * @return tone with a 22% soft fill and ink foregrounds
 */
function toneFromColor(color: string, label: string): EventTone {
  return {
    solid: color,
    soft: `color-mix(in srgb, ${color} 22%, transparent)`,
    onSolid: INK,
    onSoft: INK,
    label,
  };
}

/**
 * @brief Tone from an explicit hex colour.
 * @param hex #rrggbb
 * @param label tone label
 * @return tone
 */
export function toneFromHex(hex: string, label = "Custom"): EventTone {
  return toneFromColor(hex, label);
}

/**
 * @brief Tone for an event: explicit colour, else groupColor.
 * @param ev event fields used for colour resolution
 * @param subgroupNames subgroup id to name lookup for the label
 * @return tone
 */
export function toneForEvent(
  ev: Pick<EventItem, "visibility" | "subgroup_id" | "color">,
  subgroupNames?: Map<string, string>,
): EventTone {
  const isGroup = ev.visibility === "subgroup" && !!ev.subgroup_id;
  const label = isGroup
    ? (subgroupNames?.get(ev.subgroup_id as string) ?? "Subgroup")
    : "Community";
  if (ev.color && /^#[0-9A-Fa-f]{6}$/.test(ev.color)) {
    return toneFromColor(ev.color, label);
  }
  return toneFromColor(groupColor(isGroup ? ev.subgroup_id : null), label);
}

export const EVENT_COLOR_PRESETS: { value: string; name: string }[] = [
  { value: "#1f6feb", name: "Azure" },
  { value: "#c2410c", name: "Burnt orange" },
  { value: "#15803d", name: "Pine" },
  { value: "#7c3aed", name: "Violet" },
  { value: "#be185d", name: "Magenta" },
  { value: "#0d9488", name: "Teal" },
  { value: "#a16207", name: "Amber" },
  { value: "#0b7285", name: "Brand" },
  { value: "#dc2626", name: "Crimson" },
  { value: "#374151", name: "Slate" },
];

export function toneForSubgroupId(id: string | null): EventTone {
  return toneFromColor(groupColor(id), id ? "Subgroup" : "Community");
}
