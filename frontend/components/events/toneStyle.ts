/**
 * @file components/events/toneStyle.ts
 * @brief Inline styles for event chips: soft group-colour fill with ink text
 *        (AA on the glass surfaces). The group colour is shown as a small dot,
 *        never as a border rail.
 */
import type { CSSProperties } from "react";
import type { EventTone } from "./eventColors";

/** @brief Faint separator colour (ink at 5%) for hour lines in the week view. */
export const HAIRLINE =
  "border-[color-mix(in_srgb,var(--nx-ink)_5%,transparent)]";

/** @brief Today marker: ink circle (never bg-accent). */
export const TODAY_PILL = "bg-surface-strong font-black text-bg";

/**
 * @brief Inline style for an event chip.
 * @param tone event tone from eventColors
 * @param emphasized true for selected/all-day chips (stronger fill)
 * @return background and ink colour
 */
export function chipStyle(tone: EventTone, emphasized: boolean): CSSProperties {
  return {
    backgroundColor: `color-mix(in srgb, ${tone.solid} ${emphasized ? 40 : 22}%, transparent)`,
    color: "var(--nx-ink)",
  };
}
