"use client";
/**
 * @file components/admin/UserAgeSelect.tsx
 * @brief Per-user age group select for the admin Users table.
 */
import { useState } from "react";
import { Option, Select } from "@/components/ui";
import { TableCell } from "@/components/ui/shadcn/table";
import type { AdminUserListItem } from "@/lib/api/admin";
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
  effective,
  onSaved,
}: {
  userId: string;
  name: string;
  value?: string | null;
  /** Effective group (admin-set or from birthday). */
  effective?: string | null;
  onSaved?: () => void;
}) {
  const push = useToasts((s) => s.push);
  const [cur, setCur] = useState(value || "none");
  const [prev, setPrev] = useState(value);
  if (prev !== value) {
    setPrev(value);
    setCur(value || "none");
  }
  const [pending, setPending] = useState(false);
  const save = async (v: string) => {
    setCur(v);
    setPending(true);
    try {
      await setUserAgeGroup(userId, v === "none" ? null : (v as AgeGroup));
      onSaved?.();
    } catch (e) {
      setCur(value || "none");
      push({ variant: "danger", message: formatApiError(e) });
    } finally {
      setPending(false);
    }
  };
  return (
    <div className="flex flex-col gap-1">
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
      {effective && effective !== (value ?? "") && (
        <p className="text-xs text-muted">
          Effective: {AGE_LABEL[effective as AgeGroup] ?? effective}
        </p>
      )}
    </div>
  );
}

/**
 * @brief Table cell wrapping UserAgeSelect for an admin user row.
 * @param user row user
 * @param className cell classes
 * @param onSaved refetch callback
 * @return table cell
 */
export function UserAgeCell({
  user,
  className,
  onSaved,
}: {
  user: AdminUserListItem;
  className?: string;
  onSaved?: () => void;
}) {
  return (
    <TableCell className={className}>
      <UserAgeSelect
        userId={user.id}
        name={user.display_name || user.username}
        value={user.age_group}
        effective={user.effective_age_group}
        onSaved={onSaved}
      />
    </TableCell>
  );
}
