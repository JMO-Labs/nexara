/**
 * @file lib/auth/lastUser.ts
 * @brief Last signed-in user snapshot (localStorage) so an offline cold
 *        load can boot the shell and restore that user's persisted cache.
 *        Same lifetime as the persisted query cache; purged on sign-out.
 */
import type { CurrentUser } from "@/lib/api/users";

const KEY = "nx_last_user";
const MAX_AGE = 24 * 60 * 60 * 1000; // = PERSIST_MAX_AGE

/** @brief Remember `user` as the device's last session user. */
export function saveLastUser(user: CurrentUser): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({ at: Date.now(), user }));
  } catch {
    /* storage unavailable */
  }
}

/** @return the snapshot if fresh, else null */
export function loadLastUser(): CurrentUser | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const { at, user } = JSON.parse(raw) as { at: number; user: CurrentUser };
    return Date.now() - at < MAX_AGE && user?.id ? user : null;
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
