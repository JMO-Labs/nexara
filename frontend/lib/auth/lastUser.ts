/**
 * @file lib/auth/lastUser.ts
 * @brief Last signed-in user snapshot (localStorage) so an offline cold
 *        load can boot the shell and restore that user's persisted cache.
 *        Same lifetime as the persisted query cache; purged on sign-out.
 */
import type { CurrentUser } from "@/lib/api/users";

const KEY = "nx_last_user";

/** Only what the shell needs: no contact, address, birthday or health data. */
const SHELL_FIELDS = [
  "id",
  "username",
  "display_name",
  "avatar_url",
  "role",
  "is_admin",
  "community_id",
  "is_active",
  "two_factor_enabled",
  "tour_completed_at",
  "timezone",
] as const;
const MAX_AGE = 24 * 60 * 60 * 1000; // = PERSIST_MAX_AGE

/** @brief Remember `user` as the device's last session user. */
export function saveLastUser(user: CurrentUser): void {
  try {
    const shell = Object.fromEntries(
      SHELL_FIELDS.filter((k) => k in user).map((k) => [k, user[k]]),
    );
    localStorage.setItem(KEY, JSON.stringify({ at: Date.now(), user: shell }));
  } catch {
    /* storage unavailable */
  }
}

/** @return the snapshot (shell fields; email blank) if fresh, else null */
export function loadLastUser(): CurrentUser | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const { at, user } = JSON.parse(raw) as { at: number; user: CurrentUser };
    return Date.now() - at < MAX_AGE && user?.id
      ? { ...user, email: "" }
      : null;
  } catch {
    return null;
  }
}

/** @brief Forget the snapshot (sign-out, forced 401, account switch). */
export function clearLastUser(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable */
  }
}
