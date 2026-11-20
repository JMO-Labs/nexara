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
import { Button, EmptyState, Option, Select } from "@/components/ui";
import { PageHeader, Segmented, Toolbar } from "@/components/ui/page";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useKudosWall } from "@/hooks/useKudos";
import { KudosCard } from "./KudosCard";
import { KudosComposer } from "./KudosComposer";

const ALL_GROUPS = "__all__";
const selectCls =
  "h-9 w-auto min-w-40 rounded-full border-0 bg-[var(--nx-item)] px-4 text-sm text-ink shadow-none";

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

  const isEmpty = !wall.isLoading && !wall.isError && items.length === 0;
  const sendButton = (
    <Button className="rounded-full" onClick={() => setComposing(true)}>
      {t("sendButton")}
    </Button>
  );

  return (
    <>
      {!embedded && <PageHeader title={t("wallTitle")} actions={sendButton} />}
      <Toolbar>
        {/* Tile is narrow: embedded keeps newest-first, no sort control. */}
        {!embedded && (
          <Segmented
            label={t("sort")}
            value={sort}
            onChange={setSort}
            options={[
              { value: "newest", label: t("newest") },
              { value: "oldest", label: t("oldest") },
            ]}
          />
        )}
        <Select
          label={t("filterGroup")}
          className={selectCls}
          value={group || ALL_GROUPS}
          onValueChange={(v) => setGroup(v === ALL_GROUPS ? "" : v)}
        >
          <Option value={ALL_GROUPS}>{t("allGroups")}</Option>
          {groups.map((g) => (
            <Option key={g.id} value={g.id}>
              {g.name}
            </Option>
          ))}
        </Select>
        {embedded && !isEmpty && sendButton}
      </Toolbar>

      {wall.isError ? (
        <p role="alert">{t("error")}</p>
      ) : isEmpty ? (
        <EmptyState
          compact={embedded}
          icon={Trophy}
          title={t("emptyTitle")}
          description={t("emptyDesc")}
          action={embedded ? sendButton : undefined}
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
