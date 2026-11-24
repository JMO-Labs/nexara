"use client";
/**
 * @file components/admin/sso/GroupMappingEditor.tsx
 * @brief SSO wizard step 4: map IdP groups to a community role and/or Nexara groups.
 *
 * Stored as claim_mapping.group_mapping: group -> GroupRule[] (one rule
 * without subgroup_id for the role, one per Nexara group).
 */
import { Plus, Trash2 } from "lucide-react";
import { Button, IconButton, Input } from "@/components/ui";
import { controlClass } from "@/components/ui/Field";
import { cn } from "@/lib/utils";
import type { GroupRule } from "@/lib/api/adminOauth";
import { COMMUNITY_ROLES } from "./ProviderRules";

/** @brief One editable mapping row. */
export interface MappingRow {
  group: string;
  /** Community role, or "" for none. */
  role: string;
  subgroupIds: string[];
}

/** @brief Minimal Nexara group shape for the picker. */
export interface GroupOption {
  id: string;
  name: string;
}

/**
 * @brief Stored group_mapping -> editor rows.
 * @param mapping claim_mapping.group_mapping (single rule or list per group)
 * @return rows
 */
export function mappingToRows(
  mapping: Record<string, GroupRule | GroupRule[]> | undefined,
): MappingRow[] {
  return Object.entries(mapping ?? {}).map(([group, value]) => {
    const rules = Array.isArray(value) ? value : [value];
    return {
      group,
      role: rules.find((r) => !r.subgroup_id)?.role ?? "",
      subgroupIds: rules.flatMap((r) => (r.subgroup_id ? [r.subgroup_id] : [])),
    };
  });
}

/**
 * @brief Editor rows -> group_mapping (rows without a group or target are dropped).
 * @param rows editor rows
 * @return group -> rule list
 */
export function rowsToMapping(rows: MappingRow[]): Record<string, GroupRule[]> {
  const out: Record<string, GroupRule[]> = {};
  for (const row of rows) {
    const group = row.group.trim();
    const rules: GroupRule[] = [
      ...(row.role ? [{ subgroup_id: null, role: row.role }] : []),
      ...row.subgroupIds.map((id) => ({ subgroup_id: id, role: "member" })),
    ];
    if (group && rules.length) out[group] = [...(out[group] ?? []), ...rules];
  }
  return out;
}

/** @brief Props for GroupMappingEditor. */
export interface GroupMappingEditorProps {
  rows: MappingRow[];
  groups: GroupOption[];
  onChange: (rows: MappingRow[]) => void;
}

/**
 * @brief Mapping table; each row has its own fieldset for screen readers.
 * @param props see GroupMappingEditorProps
 * @return editor
 */
export function GroupMappingEditor({
  rows,
  groups,
  onChange,
}: GroupMappingEditorProps) {
  const update = (i: number, patch: Partial<MappingRow>) =>
    onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const toggleGroup = (i: number, id: string, on: boolean) => {
    const ids = rows[i].subgroupIds;
    update(i, {
      subgroupIds: on ? [...ids, id] : ids.filter((x) => x !== id),
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted">
        Members of an IdP group get the role and join the Nexara groups you
        pick. The highest role wins; groups are kept in sync on every sign-in.
      </p>
      {rows.length === 0 && (
        <p className="text-sm text-muted" role="status">
          No group mappings yet.
        </p>
      )}
      {rows.map((row, i) => {
        const name = row.group.trim() || `row ${i + 1}`;
        return (
          <fieldset
            key={i}
            className="glass-item flex flex-col gap-3 rounded-[22px] p-4"
          >
            <legend className="sr-only">Mapping for {name}</legend>
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Input
                  label="Provider group"
                  value={row.group}
                  placeholder="e.g. smith-family"
                  onChange={(e) => update(i, { group: e.target.value })}
                />
              </div>
              <IconButton
                variant="glass"
                aria-label={`Remove mapping ${name}`}
                onClick={() => onChange(rows.filter((_, j) => j !== i))}
              >
                <Trash2 className="size-4" aria-hidden="true" />
              </IconButton>
            </div>
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              Role
              <select
                value={row.role}
                onChange={(e) => update(i, { role: e.target.value })}
                className={cn(controlClass, "h-11 rounded-full font-normal")}
              >
                <option value="">No role change</option>
                {COMMUNITY_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>
            <fieldset className="flex flex-col gap-1.5">
              <legend className="text-sm font-medium">Nexara groups</legend>
              {groups.length === 0 ? (
                <p className="text-sm text-muted">No groups yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {groups.map((g) => (
                    <label
                      key={g.id}
                      className="glass-item flex min-h-11 items-center gap-2 rounded-full px-3 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={row.subgroupIds.includes(g.id)}
                        onChange={(e) => toggleGroup(i, g.id, e.target.checked)}
                        className="size-4 accent-[var(--nx-blue)]"
                      />
                      {g.name}
                    </label>
                  ))}
                </div>
              )}
            </fieldset>
          </fieldset>
        );
      })}
      <div>
        <Button
          type="button"
          variant="glass"
          onClick={() =>
            onChange([...rows, { group: "", role: "", subgroupIds: [] }])
          }
        >
          <Plus className="size-4" aria-hidden="true" />
          Add mapping
        </Button>
      </div>
    </div>
  );
}
