"use client";
/**
 * @file components/feed/KudosWall.tsx
 * @brief Kudos Wall: grid of kudos with group filter, sort and load-more.
 */
import * as React from "react";
import { Trophy } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button, EmptyState } from "@/components/ui";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useKudosWall } from "@/hooks/useKudos";
import { KudosCard } from "./KudosCard";
import { KudosComposer } from "./KudosComposer";

const selectCls =
  "h-10 rounded-xl border border-current/30 bg-surface px-3 text-sm";

/**
 * @brief Kudos wall page body.
 * @return wall element
 */
export function KudosWall() {
  const t = useTranslations("kudos");
  const [group, setGroup] = React.useState("");
  const [sort, setSort] = React.useState<"newest" | "oldest">("newest");
  const [composing, setComposing] = React.useState(false);
  const groups = useSubgroupList().data ?? [];
  const wall = useKudosWall();

  // Backend has no group filter/sort params yet: applied to loaded pages.
  const items = React.useMemo(() => {
    const all = (wall.data?.pages ?? []).flatMap((p) => p.kudos);
    const filtered = group ? all.filter((k) => k.subgroup_id === group) : all;
    const dir = sort === "newest" ? -1 : 1;
    return [...filtered].sort(
      (a, b) => dir * a.created_at.localeCompare(b.created_at),
    );
  }, [wall.data, group, sort]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <h1 className="mr-auto text-2xl font-black">{t("wallTitle")}</h1>
        <label className="flex flex-col gap-1 text-xs font-semibold">
          {t("filterGroup")}
          <select
            className={selectCls}
            value={group}
            onChange={(e) => setGroup(e.target.value)}
          >
            <option value="">{t("allGroups")}</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold">
          {t("sort")}
          <select
            className={selectCls}
            value={sort}
            onChange={(e) => setSort(e.target.value as "newest" | "oldest")}
          >
            <option value="newest">{t("newest")}</option>
            <option value="oldest">{t("oldest")}</option>
          </select>
        </label>
        <Button onClick={() => setComposing(true)}>{t("sendButton")}</Button>
      </div>

      {wall.isError ? (
        <p role="alert">{t("error")}</p>
      ) : !wall.isLoading && items.length === 0 ? (
        <EmptyState
          icon={Trophy}
          title={t("emptyTitle")}
          description={t("emptyDesc")}
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((k) => (
            <KudosCard
              key={k.id}
              recipient={
                k.recipient ?? { display_name: "?", avatar_url: null }
              }
              message={k.message}
              authorName={k.author_name}
              createdAt={k.created_at}
              pending={k.id.startsWith("optimistic-")}
            />
          ))}
        </div>
      )}

      {wall.hasNextPage && (
        <Button
          variant="secondary"
          onClick={() => wall.fetchNextPage()}
          disabled={wall.isFetchingNextPage}
        >
          {t("loadMore")}
        </Button>
      )}
      <KudosComposer open={composing} onClose={() => setComposing(false)} />
    </div>
  );
}

export default KudosWall;
