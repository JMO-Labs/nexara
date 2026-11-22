"use client";
/**
 * @file components/settings/TimezoneSelect.tsx
 * @brief Profile row to view and change the user's IANA time zone.
 */
import { useMutation } from "@tanstack/react-query";
import { SettingsRow } from "@/components/ui";
import { useSession } from "@/stores/session";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import { patchMe } from "@/lib/api/users";

/** @brief Zones the browser knows, plus the saved one if it is missing. */
function zones(current: string | null | undefined): string[] {
  const all = Intl.supportedValuesOf("timeZone");
  return current && !all.includes(current) ? [current, ...all] : all;
}

/** @return time zone select */
export function TimezoneSelect() {
  const user = useSession((s) => s.user);
  const setUser = useSession((s) => s.setUser);
  const push = useToasts((s) => s.push);
  const save = useMutation({
    mutationFn: (timezone: string) => patchMe({ timezone }),
    onSuccess: (u) => {
      setUser(u);
      push({ variant: "success", message: "Time zone saved" });
    },
    onError: (err) => push({ variant: "danger", message: formatApiError(err) }),
  });
  if (!user) return null;
  return (
    <SettingsRow
      label="Time zone"
      description="Used for reminders, the weekly recap and quiet hours."
    >
      <select
        aria-label="Time zone"
        value={user.timezone ?? ""}
        disabled={save.isPending}
        onChange={(e) => save.mutate(e.target.value)}
        className="glass-item h-11 w-full rounded-full px-4 text-sm focus-visible:outline-2 focus-visible:outline-accent"
      >
        {!user.timezone && (
          <option value="" disabled>
            Not set
          </option>
        )}
        {zones(user.timezone).map((z) => (
          <option key={z} value={z}>
            {z.replaceAll("_", " ")}
          </option>
        ))}
      </select>
    </SettingsRow>
  );
}
