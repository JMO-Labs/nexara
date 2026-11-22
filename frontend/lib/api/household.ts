/**
 * @file lib/api/household.ts
 * @brief Household members and pets (no accounts), their tagged photos
 *        and upcoming birthdays / gotcha days.
 */
import { apiDelete, apiGet, apiPatch, apiPost, seg } from "./client";
import type { ProfileLevel } from "@/lib/profile";
import type { TaggedPage } from "./tags";

export type HouseholdKind = "person" | "pet";

export interface HouseholdMember {
  id: string;
  owner_id: string;
  kind: HouseholdKind;
  name: string;
  /** @handle for mentions (stable across renames). */
  handle: string | null;
  relation: string | null;
  /** ISO date, or "--MM-DD" when the year is hidden. */
  birthday: string | null;
  show_birth_year: boolean;
  photo_media_id: string | null;
  visibility: ProfileLevel;
  bio: string | null;
  species: string | null;
  breed: string | null;
  gotcha_day: string | null;
  likes: string[];
  dislikes: string[];
  care_card: string | null;
  care_visibility: ProfileLevel;
  can_edit: boolean;
}

export type HouseholdInput = Partial<
  Omit<HouseholdMember, "id" | "owner_id" | "can_edit">
>;

export interface Celebration {
  member: HouseholdMember;
  occasion: "birthday" | "gotcha_day";
  in_days: number;
}

const base = "/api/v1/household";

export const listHousehold = () => apiGet<HouseholdMember[]>(base);
export const listUserHousehold = (userId: string) =>
  apiGet<HouseholdMember[]>(`/api/v1/users/${seg(userId)}/household`);
export const getHouseholdMember = (id: string) =>
  apiGet<HouseholdMember>(`${base}/${seg(id)}`);
export const createHouseholdMember = (body: HouseholdInput) =>
  apiPost<HouseholdMember>(base, body);
export const updateHouseholdMember = (id: string, body: HouseholdInput) =>
  apiPatch<HouseholdMember>(`${base}/${seg(id)}`, body);
export const deleteHouseholdMember = (id: string) =>
  apiDelete<{ message: string }>(`${base}/${seg(id)}`);
export const upcomingCelebrations = () =>
  apiGet<Celebration[]>(`${base}/upcoming`);
export const householdPhotos = (id: string, before?: string | null) =>
  apiGet<TaggedPage>(
    `${base}/${seg(id)}/tagged${before ? `?${new URLSearchParams({ before })}` : ""}`,
  );
