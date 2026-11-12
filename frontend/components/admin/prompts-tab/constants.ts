/**
 * @file components/admin/prompts-tab/constants.ts
 * @brief Shared constants for the prompts admin tab.
 */
import type { BadgeProps } from "@/components/ui";

export const FREQUENCIES = [
  { value: "annual_date", label: "Annual date" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "custom", label: "Custom" },
  { value: "one_time", label: "One time" },
] as const;

/** @brief Weekday labels indexed 0 (Monday) to 6, matching backend. */
export const WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;

const FREQUENCY_TONES: Record<string, NonNullable<BadgeProps["tone"]>> = {
  annual_date: "sun",
  weekly: "accent",
  monthly: "leaf",
  custom: "neutral",
  one_time: "leaf",
};

/**
 * @brief Badge tone for a prompt frequency.
 * @param frequency frequency key
 * @return badge tone
 */
export function frequencyTone(
  frequency: string,
): NonNullable<BadgeProps["tone"]> {
  return FREQUENCY_TONES[frequency] ?? "neutral";
}
