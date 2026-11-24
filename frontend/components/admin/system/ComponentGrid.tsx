/**
 * @file components/admin/system/ComponentGrid.tsx
 * @brief Component health cards; status is icon + word, never colour alone.
 */
import { AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import type { ComponentStatus, SystemComponent } from "@/lib/api/adminSystem";

const STATUS = {
  ok: { Icon: CheckCircle, label: "Healthy", cls: "text-ok" },
  warn: { Icon: AlertTriangle, label: "Needs attention", cls: "text-warn" },
  down: { Icon: XCircle, label: "Down", cls: "text-danger" },
} satisfies Record<ComponentStatus, object>;

/**
 * @brief Grid of monitored components.
 * @param components components to show
 * @return list element
 */

/** @brief Friendly names for health components. */
const LABELS: Record<string, string> = {
  database: "Database",
  valkey: "Cache (Valkey)",
  workers: "Background workers",
  queues: "Job queues",
  beat: "Scheduler",
  email: "Email",
  push: "Push notifications",
};
export function ComponentGrid({
  components,
}: {
  components: SystemComponent[];
}) {
  return (
    <ul
      aria-label="System components"
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
    >
      {components.map((c) => {
        const { Icon, label, cls } = STATUS[c.status] ?? STATUS.warn;
        return (
          <li key={c.name} className="glass-item min-w-0 rounded-[22px] p-3">
            <p className="truncate text-sm font-medium">
              {LABELS[c.name] ?? c.name}
            </p>
            <p className="mt-1 flex items-center gap-1.5 text-sm">
              <Icon aria-hidden="true" className={`size-4 shrink-0 ${cls}`} />
              {label}
            </p>
            {c.detail && (
              <p className="mt-1 break-words text-xs text-muted">{c.detail}</p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
