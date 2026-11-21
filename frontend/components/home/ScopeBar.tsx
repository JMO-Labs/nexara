"use client";
/**
 * @file components/home/ScopeBar.tsx
 * @brief Scope pills (Everything + member groups) beside a "needs you" slot.
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import { groupColor } from "@/lib/groupColor";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useHomeScope } from "@/stores/homeScope";

/**
 * @brief Scope filter bar.
 * @param needs slot rendered in the right-hand glass group
 * @return strip row
 */
export function ScopeBar({ needs }: { needs: React.ReactNode }) {
  const { data } = useSubgroupList();
  const scope = useHomeScope((s) => s.scope);
  const setScope = useHomeScope((s) => s.setScope);
  const groups = (data ?? []).filter((g) => g.is_member);
  const pill = (active: boolean) =>
    cn(
      "flex shrink-0 items-center gap-2 rounded-full px-3.5 py-1.5 text-sm transition-colors",
      active ? "bg-[var(--nx-ink)] text-[var(--nx-bg)]" : "hover:bg-white/30",
    );
  return (
    <div className="mb-4 flex flex-col gap-2.5 md:mb-[18px] md:flex-row md:items-center md:gap-3">
      <div
        role="group"
        aria-label="Scope"
        className="glass flex items-center gap-1 overflow-x-auto whitespace-nowrap rounded-full p-1"
      >
        <button
          type="button"
          aria-pressed={scope === "all"}
          onClick={() => setScope("all")}
          className={pill(scope === "all")}
        >
          Everything
        </button>
        {groups.map((g) => (
          <button
            key={g.id}
            type="button"
            aria-pressed={scope === g.id}
            onClick={() => setScope(g.id)}
            className={pill(scope === g.id)}
          >
            <span
              aria-hidden
              className="h-2 w-2 rounded-full"
              style={{ background: groupColor(g.id, g.accent_color) }}
            />
            {g.name}
          </button>
        ))}
      </div>
      <div className="flex min-w-0 items-center gap-2 overflow-x-auto whitespace-nowrap md:ml-auto">
        {needs}
      </div>
    </div>
  );
}
