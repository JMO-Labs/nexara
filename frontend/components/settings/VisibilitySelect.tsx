"use client";
/**
 * @file components/settings/VisibilitySelect.tsx
 * @brief Per-field "who can see this" picker. Saves on change and refreshes
 *        the own-profile query that holds the resolved levels.
 */
import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Eye } from "lucide-react";
import { useMemberProfile } from "@/hooks/useMembers";
import { updateProfile } from "@/lib/api/settings";
import { LEVEL_LABEL, type ProfileLevel } from "@/lib/profile";
import { qk } from "@/lib/query-keys";
import { useSession } from "@/stores/session";

/**
 * @brief Resolved privacy levels for the signed-in user.
 * @return map field -> level (empty while loading)
 */
export function useMyLevels(): Record<string, ProfileLevel> {
  const me = useSession((s) => s.user?.id) ?? "";
  return useMemberProfile(me).data?.field_visibility ?? {};
}

/**
 * @brief Picker for one field.
 * @param field profile field name
 * @param label field name for the accessible label
 * @return select element
 */
export function VisibilitySelect({
  field,
  label,
}: {
  field: string;
  label: string;
}) {
  const qc = useQueryClient();
  const me = useSession((s) => s.user?.id) ?? "";
  const levels = useMyLevels();
  const [value, setValue] = React.useState<ProfileLevel | null>(null);
  const current = value ?? levels[field] ?? "private";
  const save = useMutation({
    mutationFn: (v: ProfileLevel) =>
      updateProfile({ field_visibility: { [field]: v } }),
    onSuccess: () =>
      void qc.invalidateQueries({ queryKey: qk.people.profile(me) }),
    onError: () => setValue(null),
  });
  return (
    <label className="glass-item relative flex h-10 w-[8.75rem] shrink-0 items-center gap-1.5 rounded-full pr-3 pl-3 text-xs text-muted focus-within:outline-2 focus-within:outline-accent">
      <Eye className="size-3.5" aria-hidden />
      <span className="sr-only">Who can see your {label}</span>
      <select
        value={current}
        disabled={save.isPending}
        onChange={(e) => {
          const v = e.target.value as ProfileLevel;
          setValue(v);
          save.mutate(v);
        }}
        className="cursor-pointer appearance-none bg-transparent pr-1 text-xs text-ink outline-none"
      >
        {(Object.keys(LEVEL_LABEL) as ProfileLevel[]).map((l) => (
          <option key={l} value={l} className="bg-[var(--nx-glass-solid)]">
            {LEVEL_LABEL[l]}
          </option>
        ))}
      </select>
    </label>
  );
}
