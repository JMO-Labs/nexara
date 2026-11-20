/**
 * @file components/events/toneStyle.ts
 * @brief Inline styles for event chips: soft group-colour fill, 3px group
 *        colour left bar, ink text (AA on the glass surfaces).
 */
import type { CSSProperties } from "react";
import type { EventTone } from "./eventColors";

/** @brief Hairline border colour (ink at 8%) for calendar cell separators. */
export const HAIRLINE =
  "border-[color-mix(in_srgb,var(--nx-ink)_8%,transparent)]";

/** @brief Today marker: ink circle (never bg-accent). */
export const TODAY_PILL = "bg-surface-strong font-black text-bg";

/**
 * @brief Inline style for an event chip.
 * @param tone event tone from eventColors
 * @param emphasized true for selected/all-day chips (stronger fill)
 * @return background, ink color and left-bar border color
 */
export function chipStyle(tone: EventTone, emphasized: boolean): CSSProperties {
  return {
    backgroundColor: `color-mix(in srgb, ${tone.solid} ${emphasized ? 40 : 22}%, transparent)`,
    color: "var(--nx-ink)",
    borderColor: tone.solid,
  };
}
