"use client";
/**
 * @file components/admin/sso/GroupMappingEditor.tsx
 * @brief SSO wizard step 4: map IdP groups to a community role and/or Nexara groups.
 *
 * Stored as claim_mapping.group_mapping: group -> GroupRule | GroupRule[]
 * (rules without subgroup_id grant a community role, the others a subgroup
 * membership with its own role). Rows keep the stored rules verbatim, so
 * mappingToRows -> rowsToMapping is the identity for untouched rows.
 */
import { Plus, Trash2 } from "lucide-react";
import { Button, IconButton, Input } from "@/components/ui";
import { controlClass } from "@/components/ui/Field";
import { cn } from "@/lib/utils";
import type { GroupRule } from "@/lib/api/adminOauth";
import { COMMUNITY_ROLES } from "./ProviderRules";

/** @brief Roles a member can hold inside a Nexara group (highest first). */
export const GROUP_ROLES = ["owner", "moderator", "member"] as const;

/** @brief One editable mapping row (rules kept exactly as stored). */
export interface MappingRow {
  group: string;
  rules: GroupRule[];
  /** Stored as a list (false: a single rule object). */
  list: boolean;
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
  return Object.entries(mapping ?? {}).map(([group, value]) => ({
    group,
    rules: Array.isArray(value) ? [...value] : [value],
    list: Array.isArray(value),
  }));
}

/**
 * @brief Editor rows -> group_mapping (rows without a group or rules are dropped).
 * @param rows editor rows
 * @return group -> rule (single-rule rows that were stored as an object) or rule list
 */
export function rowsToMapping(
  rows: MappingRow[],
): Record<string, GroupRule | GroupRule[]> {
  const out: Record<string, GroupRule | GroupRule[]> = {};
  for (const row of rows) {
    const group = row.group.trim();
    if (!group || row.rules.length === 0) continue;
    const prev = out[group];
    if (prev !== undefined) {
      out[group] = [...(Array.isArray(prev) ? prev : [prev]), ...row.rules];
    } else {
      out[group] =
        !row.list && row.rules.length === 1 ? row.rules[0] : [...row.rules];
    }
  }
  return out;
}

/** @brief Highest role among ``roles`` by ``order`` (first = highest), or "". */
function highest(roles: string[], order: readonly string[]): string {
  return (
    [...order].find((r) => roles.includes(r)) ??
    roles.find((r) => !order.includes(r)) ??
    ""
  );
}

/**
 * @brief Replace the rules matching ``match`` with ``next`` at the first match's position.
 * @return new rule list
 */
function replaceRules(
  rules: GroupRule[],
  match: (r: GroupRule) => boolean,
  next: GroupRule[],
): GroupRule[] {
  const at = rules.findIndex(match);
  const kept = rules.filter((r) => !match(r));
  const pos =
    at < 0 ? kept.length : rules.slice(0, at).filter((r) => !match(r)).length;
  return [...kept.slice(0, pos), ...next, ...kept.slice(pos)];
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
  const isRole = (r: GroupRule) => !r.subgroup_id;
  const forGroup = (id: string) => (r: GroupRule) => r.subgroup_id === id;

  const setRole = (i: number, role: string) =>
    update(i, {
      rules: replaceRules(
        rows[i].rules,
        isRole,
        role ? [{ subgroup_id: null, role }] : [],
      ),
    });
  const setGroup = (i: number, id: string, role: string | null) =>
    update(i, {
      rules: replaceRules(
        rows[i].rules,
        forGroup(id),
        role ? [{ subgroup_id: id, role }] : [],
      ),
    });

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
        const role = highest(
          row.rules.filter(isRole).map((r) => r.role),
          [...COMMUNITY_ROLES].reverse(),
        );
        const known = new Set(groups.map((g) => g.id));
        const unknown = row.rules.filter(
          (r) => r.subgroup_id && !known.has(r.subgroup_id),
        ).length;
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
                value={role}
                onChange={(e) => setRole(i, e.target.value)}
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
                <ul className="flex flex-col gap-2">
                  {groups.map((g) => {
                    const held = row.rules
                      .filter(forGroup(g.id))
                      .map((r) => r.role);
                    const on = held.length > 0;
                    return (
                      <li
                        key={g.id}
                        className="flex flex-wrap items-center gap-2"
                      >
                        <label className="glass-item flex min-h-11 items-center gap-2 rounded-full px-3 text-sm">
                          <input
                            type="checkbox"
                            checked={on}
                            onChange={(e) =>
                              setGroup(
                                i,
                                g.id,
                                e.target.checked ? "member" : null,
                              )
                            }
                            className="size-4 accent-[var(--nx-blue)]"
                          />
                          {g.name}
                        </label>
                        {on && (
                          <select
                            aria-label={`Role in ${g.name}`}
                            value={highest(held, GROUP_ROLES)}
                            onChange={(e) => setGroup(i, g.id, e.target.value)}
                            className={cn(
                              controlClass,
                              "h-11 w-auto rounded-full",
                            )}
                          >
                            {GROUP_ROLES.map((r) => (
                              <option key={r} value={r}>
                                {r}
                              </option>
                            ))}
                          </select>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
              {unknown > 0 && (
                <p className="text-sm text-muted">
                  {unknown} rule(s) for groups that no longer exist are kept.
                </p>
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
            onChange([...rows, { group: "", rules: [], list: true }])
          }
        >
          <Plus className="size-4" aria-hidden="true" />
          Add mapping
        </Button>
      </div>
    </div>
  );
}
