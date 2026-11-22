"use client";
/**
 * @file components/settings/TimezoneSync.tsx
 * @brief Renders nothing. When the signed-in user has no timezone saved,
 *        saves the browser's zone once so reminders use local time.
 */
import { useEffect, useRef } from "react";
import { useSession } from "@/stores/session";
import { patchMe } from "@/lib/api/users";

/** @return null */
export function TimezoneSync() {
  const user = useSession((s) => s.user);
  const setUser = useSession((s) => s.setUser);
  const sent = useRef(false);
  const needs = !!user && user.timezone == null;

  useEffect(() => {
    if (!needs || sent.current) return;
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (!tz) return;
    sent.current = true;
    patchMe({ timezone: tz })
      .then(setUser)
      .catch(() => {
        // Best effort; reminders fall back to UTC.
      });
  }, [needs, setUser]);
  return null;
}
