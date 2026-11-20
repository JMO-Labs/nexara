"use client";
/**
 * @file components/subgroups/groups-page/GroupsPage.tsx
 * @brief Groups index: PageHeader, Toolbar (search, All/Open/Private, Everyone/Mine)
 *        and a glass card grid.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui";
import {
  PageHeader,
  Toolbar,
  SearchField,
  Segmented,
} from "@/components/ui/page";
import { GroupMosaic } from "@/components/subgroups/groups-page/GroupMosaic";
import { CreateSubgroupModal } from "@/components/subgroups/CreateSubgroupModal";
import {
  useSubgroupList,
  useJoinSubgroup,
  useLeaveSubgroup,
} from "@/hooks/useSubgroups";

type FilterMode = "all" | "open" | "private";
type Scope = "everyone" | "mine";

const FILTERS: { value: FilterMode; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "private", label: "Private" },
];
const SCOPES: { value: Scope; label: string }[] = [
  { value: "everyone", label: "Everyone" },
  { value: "mine", label: "Mine" },
];

/**
 * @brief Groups index page body.
 * @return page content
 */
export function GroupsPage() {
  const router = useRouter();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [filter, setFilter] = React.useState<FilterMode>("all");
  const [scope, setScope] = React.useState<Scope>("everyone");

  const { data, isLoading, error, refetch } = useSubgroupList();
  const join = useJoinSubgroup();
  const leave = useLeaveSubgroup();

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data ?? []).filter((g) => {
      if (scope === "mine" && !g.is_member) return false;
      if (filter === "open" && g.join_policy !== "open") return false;
      if (filter === "private" && !g.is_private) return false;
      if (!q) return true;
      return (
        g.name.toLowerCase().includes(q) ||
        g.slug.toLowerCase().includes(q) ||
        (g.description ?? "").toLowerCase().includes(q)
      );
    });
  }, [data, query, filter, scope]);

  const total = data?.length ?? 0;

  return (
    <>
      <PageHeader
        title="Groups"
        description={`${total} ${total === 1 ? "circle" : "circles"} in the community`}
        actions={<Button onClick={() => setCreateOpen(true)}>New group</Button>}
      />
      <Toolbar>
        <SearchField
          value={query}
          onChange={setQuery}
          placeholder="Search groups…"
          label="Search groups"
        />
        <Segmented
          label="Filter groups"
          options={FILTERS}
          value={filter}
          onChange={setFilter}
        />
        <Segmented
          label="Group scope"
          options={SCOPES}
          value={scope}
          onChange={setScope}
        />
      </Toolbar>
      <GroupMosaic
        data={filtered}
        isLoading={isLoading}
        error={error}
        onSelect={(s) => router.push(`/app/subgroups/${s}`)}
        onJoin={(s) => join.mutate(s)}
        onLeave={(s) => leave.mutate(s)}
        joinBusy={join.isPending ? join.variables : null}
        leaveBusy={leave.isPending ? leave.variables : null}
        onCreate={() => setCreateOpen(true)}
        onRetry={() => refetch()}
        isFiltered={total > 0}
      />
      <CreateSubgroupModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />
    </>
  );
}

export default GroupsPage;
