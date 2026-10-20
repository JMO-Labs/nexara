/**
 * @file components/events/subscriptions/intervals.ts
 * @brief Sync interval options (minutes) shared by row and add modal.
 */
export const INTERVALS: Array<[number, string, string]> = [
  [15, "15 min", "Every 15 minutes"],
  [30, "30 min", "Every 30 minutes"],
  [60, "1 hr", "Every hour"],
  [180, "3 hrs", "Every 3 hours"],
  [720, "12 hrs", "Every 12 hours"],
];
