/**
 * @file components/admin/PluginPermissionList.tsx
 * @brief Permission list with descriptions; sensitive and new ones flagged.
 */
import { AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui";
import {
  describePermission,
  SENSITIVE_PERMISSIONS,
} from "@/lib/pluginPermissions";

/**
 * @brief Render permissions with descriptions.
 * @param permissions permission ids
 * @param newPermissions ids to highlight as newly requested
 * @return list element
 */
export function PluginPermissionList({
  permissions,
  newPermissions = [],
}: {
  permissions: string[];
  newPermissions?: string[];
}) {
  if (permissions.length === 0)
    return <p className="text-sm text-muted">No permissions requested.</p>;
  return (
    <ul className="flex flex-col gap-2" aria-label="Permissions">
      {permissions.map((p) => {
        const sensitive = SENSITIVE_PERMISSIONS.has(p);
        return (
          <li
            key={p}
            data-testid={`perm-${p}`}
            data-sensitive={sensitive ? "true" : undefined}
            className={
              "flex flex-col gap-0.5 rounded-xl border p-2 " +
              (sensitive
                ? "border-destructive/60 bg-destructive/10"
                : "border-ink/10")
            }
          >
            <span className="flex flex-wrap items-center gap-2 font-mono text-sm font-semibold">
              {sensitive && (
                <AlertTriangle
                  className="size-4 text-destructive"
                  aria-label="Sensitive permission"
                />
              )}
              <span>{p}</span>
              {newPermissions.includes(p) && <Badge>New</Badge>}
            </span>
            <span className="text-sm text-muted">{describePermission(p)}</span>
          </li>
        );
      })}
    </ul>
  );
}
