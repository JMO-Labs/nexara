/**
 * @file components/events/toneStyle.ts
 * @brief AA-safe inline colors for event chips. Community tone uses the brand
 *        accent token (light lavender), so it gets dark ink text instead of white.
 */
import type { CSSProperties } from "react";
import type { EventTone } from "./eventColors";

/**
 * @brief Inline style for an event chip.
 * @param tone event tone from eventColors
 * @param solid true for filled chip, false for soft chip
 * @return background, color and border color
 */
export function chipStyle(tone: EventTone, solid: boolean): CSSProperties {
  const brand = tone.solid.startsWith("var(");
  if (brand) {
    return {
      backgroundColor: solid
        ? "var(--nx-accent)"
        : "color-mix(in srgb, var(--nx-accent) 40%, transparent)",
      color: "var(--nx-surface-strong)",
      borderColor: "var(--nx-accent)",
    };
  }
  return {
    backgroundColor: solid ? tone.solid : tone.soft,
    color: solid ? tone.onSolid : tone.onSoft,
    borderColor: tone.solid,
  };
}
