"use client";
/**
 * @file components/feed/KudosWall.tsx
 * @brief Kudos Wall: grid of kudos with group filter, sort and load-more.
 *        Embedded mode (Home feed tile) drops the page header and uses a
 *        single-column list.
 */
import * as React from "react";
import { Trophy } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button, EmptyState } from "@/components/ui";
import { PageHeader, Segmented, Toolbar } from "@/components/ui/page";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useKudosWall } from "@/hooks/useKudos";
import { KudosCard } from "./KudosCard";
import { KudosComposer } from "./KudosComposer";

const selectCls =
  "glass-btn h-9 rounded-full px-3 text-sm text-ink outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

export interface KudosWallProps {
  /** Home feed tile: no page header, compact toolbar, single column. */
  embedded?: boolean;
}

/**
 * @brief Kudos wall page body.
 * @param embedded compact in-tile layout
 * @return wall element
 */
export function KudosWall({ embedded = false }: KudosWallProps = {}) {
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

  const sendButton = (
    <Button className="rounded-full" onClick={() => setComposing(true)}>
      {t("sendButton")}
    </Button>
  );

  return (
    <>
      {!embedded && <PageHeader title={t("wallTitle")} actions={sendButton} />}
      <Toolbar>
        <Segmented
          label={t("sort")}
          value={sort}
          onChange={setSort}
          options={[
            { value: "newest", label: t("newest") },
            { value: "oldest", label: t("oldest") },
          ]}
        />
        <select
          aria-label={t("filterGroup")}
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
        {embedded && sendButton}
      </Toolbar>

      {wall.isError ? (
        <p role="alert">{t("error")}</p>
      ) : !wall.isLoading && items.length === 0 ? (
        <EmptyState
          icon={Trophy}
          title={t("emptyTitle")}
          description={t("emptyDesc")}
        />
      ) : (
        <div
          className={
            embedded
              ? "flex flex-col gap-3"
              : "grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
          }
        >
          {items.map((k) => (
            <KudosCard
              key={k.id}
              recipient={k.recipient ?? { display_name: "?", avatar_url: null }}
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
          className="mx-auto mt-4"
          onClick={() => wall.fetchNextPage()}
          disabled={wall.isFetchingNextPage}
        >
          {t("loadMore")}
        </Button>
      )}
      <KudosComposer open={composing} onClose={() => setComposing(false)} />
    </>
  );
}

export default KudosWall;
