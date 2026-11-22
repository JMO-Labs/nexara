/**
 * @file lib/api/celebrations.ts
 * @brief Calendar celebrations: birthdays (people, pets) and gotcha days.
 */
import { apiGet } from "./client";

export interface CalendarCelebration {
  date: string; // YYYY-MM-DD
  occasion: "birthday" | "gotcha_day";
  subject_type: "user" | "household";
  subject_id: string;
  name: string;
  is_pet: boolean;
  link: string;
}

/** @brief Celebrations from start to end (inclusive, YYYY-MM-DD). */
export const listCelebrations = (start: string, end: string) =>
  apiGet<CalendarCelebration[]>(
    `/api/v1/calendar/celebrations?start=${start}&end=${end}`,
  );
