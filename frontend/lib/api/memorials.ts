/**
 * @file lib/api/memorials.ts
 * @brief Memorials: a household member's passed-on date and admin
 *        memorialize / restore of an account.
 */
import { apiPost, apiPut, seg } from "./client";
import type { HouseholdMember } from "./household";

/** @brief Set (or clear with null) a household member's passed-on date. */
export const setPassedOn = (memberId: string, passedOn: string | null) =>
  apiPut<HouseholdMember>(`/api/v1/household/${seg(memberId)}/passed-on`, {
    passed_on: passedOn,
  });

/** @brief Admin: memorialize an account (date optional, YYYY-MM-DD). */
export const memorializeUser = (userId: string, passedOn: string | null) =>
  apiPost<{ message: string }>(
    `/api/v1/admin/users/${seg(userId)}/memorialize`,
    { passed_on: passedOn },
  );

/** @brief Admin: restore a memorialized account. */
export const unmemorializeUser = (userId: string) =>
  apiPost<{ message: string }>(
    `/api/v1/admin/users/${seg(userId)}/unmemorialize`,
  );
