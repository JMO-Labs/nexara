"use client";
/**
 * @file components/subgroups/groups-page/GroupMosaic.tsx
 * @brief Auto-fill grid (min 260px columns) of glass group cards with
 *        error / loading / empty states.
 */
import * as React from "react";
import { Button, Skeleton, EmptyState } from "@/components/ui";
import { SubgroupCard } from "@/components/subgroups/SubgroupCard";
import { MemberStack } from "./MemberStack";
import type { Subgroup } from "@/lib/api/subgroups";

export interface GroupMosaicProps {
  data: Subgroup[];
  isLoading: boolean;
  error: unknown;
  onSelect: (s: string) => void;
  onJoin: (s: string) => void;
  onLeave: (s: string) => void;
  joinBusy: string | null | undefined;
  leaveBusy: string | null | undefined;
  onCreate: () => void;
  /** Retry handler for the error state (defaults to page reload). */
  onRetry?: () => void;
  /** True when a search/filter hid otherwise existing groups. */
  isFiltered?: boolean;
}

/** Auto-fill columns (min 260px) so a few cards do not leave a large empty area. */
const GRID =
  "grid grid-cols-[repeat(auto-fill,minmax(min(100%,260px),1fr))] gap-3 md:gap-[18px]";

/**
 * @brief Group card grid.
 * @param props list data, query state and action callbacks
 * @return grid or fallback state
 */
export function GroupMosaic({
  data,
  isLoading,
  error,
  onSelect,
  onJoin,
  onLeave,
  joinBusy,
  leaveBusy,
  onCreate,
  onRetry,
  isFiltered = false,
}: GroupMosaicProps) {
  if (error) {
    return (
      <EmptyState
        title="Couldn't load groups"
        description={error instanceof Error ? error.message : String(error)}
        action={
          <Button
            variant="secondary"
            onClick={onRetry ?? (() => window.location.reload())}
          >
            Retry
          </Button>
        }
      />
    );
  }
  if (isLoading) {
    return (
      <div
        className={GRID}
        role="status"
        aria-busy="true"
        aria-label="Loading groups"
      >
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height={300} />
        ))}
      </div>
    );
  }
  if (data.length === 0) {
    return isFiltered ? (
      <EmptyState
        title="No groups match"
        description="Try a different filter or start a new circle."
        action={<Button onClick={onCreate}>Create group</Button>}
      />
    ) : (
      <EmptyState
        title="No groups yet"
        description="Create one to organize conversations and events around a smaller circle."
        action={<Button onClick={onCreate}>Create group</Button>}
      />
    );
  }

  return (
    <div className={GRID}>
      {data.map((g) => (
        <SubgroupCard
          key={g.id}
          subgroup={g}
          isMember={g.is_member}
          onSelect={onSelect}
          onJoin={onJoin}
          onLeave={onLeave}
          busy={joinBusy === g.slug || leaveBusy === g.slug}
          avatars={
            <MemberStack
              slug={g.slug}
              preview={g.member_preview}
              count={g.member_count}
            />
          }
        />
      ))}
    </div>
  );
}

export default GroupMosaic;
