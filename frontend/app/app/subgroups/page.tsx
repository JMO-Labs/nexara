"use client";
/**
 * @file app/app/subgroups/page.tsx
 * @brief Groups index — masthead, sticky toolbar, mosaic of group tiles. Drawer routing preserved
 *        via ?subgroup=<slug>.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Button, Input } from "@/components/ui";
import { GroupMosaic } from "@/components/subgroups/groups-page/GroupMosaic";
import { CreateSubgroupModal } from "@/components/subgroups/CreateSubgroupModal";
import { PageMasthead } from "@/components/layout/PageMasthead";
import {
  useSubgroupList,
  useJoinSubgroup,
  useLeaveSubgroup,
} from "@/hooks/useSubgroups";

type FilterMode = "all" | "open" | "private";

export default function SubgroupsPage() {
  const router = useRouter();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [filter, setFilter] = React.useState<FilterMode>("all");

  const { data, isLoading, error, refetch } = useSubgroupList();
  const join = useJoinSubgroup();
  const leave = useLeaveSubgroup();

  const select = (s: string) => {
    router.push(`/app/subgroups/${s}`);
  };

  const filtered = React.useMemo(() => {
    const list = data ?? [];
    const q = query.trim().toLowerCase();
    return list.filter((g) => {
      if (filter === "open" && g.join_policy !== "open") return false;
      if (filter === "private" && !g.is_private) return false;
      // TODO: Add is_member flag to Subgroup type when available,
      // then filter: if (g.is_private && !is_member) return false;
      // For now, trust backend filtering for private group visibility.
      if (!q) return true;
      return (
        g.name.toLowerCase().includes(q) ||
        g.slug.toLowerCase().includes(q) ||
        (g.description ?? "").toLowerCase().includes(q)
      );
    });
  }, [data, query, filter]);

  const total = data?.length ?? 0;

  return (
    <div className="relative min-h-screen w-full px-4 pb-20 md:px-12 lg:px-16">
      <PageMasthead
        title="Groups"
        meta={`${total} ${total === 1 ? "circle" : "circles"} in the community`}
        right={<Button onClick={() => setCreateOpen(true)}>+ New group</Button>}
      />

      <div className="bg-bg/80 sticky top-0 z-[5] -mx-4 mb-8 border-y border-current/10 px-4 py-3 backdrop-blur md:-mx-12 md:mb-12 md:px-12 lg:-mx-16 lg:px-16">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
          <div className="min-w-0 flex-1 sm:max-w-[420px]">
            <Input
              type="search"
              aria-label="Search groups"
              placeholder="Search groups…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div role="group" aria-label="Filter groups" className="flex gap-1.5">
            {(["all", "open", "private"] as FilterMode[]).map((m) => (
              <button
                key={m}
                type="button"
                aria-pressed={filter === m}
                onClick={() => setFilter(m)}
                className={`min-h-11 rounded-full px-4 text-xs uppercase tracking-widest outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
                  filter === m ? "bg-accent text-surface-strong" : "bg-surface"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-baseline gap-4 border-b border-current/10 pb-3">
        <h2 className="text-[22px] font-semibold capitalize tracking-tight md:text-[28px]">
          {query
            ? "Results"
            : filter === "all"
              ? "All groups"
              : `${filter} groups`}
        </h2>
        <p className="ml-auto text-sm text-muted">
          {query
            ? `for "${query}"`
            : `${filtered.length} ${filtered.length === 1 ? "circle" : "circles"}`}
        </p>
      </div>

      <div className="mt-6">
        <GroupMosaic
          data={filtered}
          isLoading={isLoading}
          error={error}
          onSelect={select}
          onJoin={(s) => join.mutate(s)}
          onLeave={(s) => leave.mutate(s)}
          joinBusy={join.isPending ? join.variables : null}
          leaveBusy={leave.isPending ? leave.variables : null}
          onCreate={() => setCreateOpen(true)}
          onRetry={() => refetch()}
          isFiltered={total > 0}
        />
      </div>

      <CreateSubgroupModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />
    </div>
  );
}
