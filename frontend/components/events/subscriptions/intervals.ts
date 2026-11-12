/**
 * @file components/events/subscriptions/intervals.ts
 * @brief Sync frequency options (minutes) shared by row and add/edit modal.
 */
export const INTERVALS: Array<[number, string, string]> = [
  [60, "Hourly", "Hourly"],
  [1440, "Daily", "Daily"],
  [10080, "Weekly", "Weekly"],
];
