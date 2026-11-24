"use client";
/**
 * @file components/admin/UserAgeSelect.tsx
 * @brief Per-user age group select for the admin Users table.
 */
import { useState } from "react";
import { Option, Select } from "@/components/ui";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import {
  AGE_GROUPS,
  AGE_LABEL,
  setUserAgeGroup,
  type AgeGroup,
} from "@/lib/api/ageGroups";

/**
 * @brief Select to set or clear a user's age group.
 * @param userId user id
 * @param name display name (for the aria-label)
 * @param value current group, if known
 * @return select
 */
export function UserAgeSelect({
  userId,
  name,
  value,
}: {
  userId: string;
  name: string;
  value?: string | null;
}) {
  const push = useToasts((s) => s.push);
  const [cur, setCur] = useState(value || "none");
  const [pending, setPending] = useState(false);
  const save = async (v: string) => {
    setCur(v);
    setPending(true);
    try {
      await setUserAgeGroup(userId, v === "none" ? null : (v as AgeGroup));
    } catch (e) {
      setCur(value || "none");
      push({ variant: "danger", message: formatApiError(e) });
    } finally {
      setPending(false);
    }
  };
  return (
    <Select
      label={`Age group for ${name}`}
      value={cur}
      disabled={pending}
      onValueChange={save}
    >
      <Option value="none">{AGE_LABEL.unknown}</Option>
      {AGE_GROUPS.map((g) => (
        <Option key={g} value={g}>
          {AGE_LABEL[g]}
        </Option>
      ))}
    </Select>
  );
}
