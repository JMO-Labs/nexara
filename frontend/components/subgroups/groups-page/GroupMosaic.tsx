"use client";
/**
 * @file components/subgroups/groups-page/GroupMosaic.tsx
 * @brief Responsive mosaic of group tiles (every 5th tile spans 2 cols on
 *        wider screens) with error / loading / empty states.
 */
import * as React from "react";
import { motion } from "framer-motion";
import { Button, Skeleton, EmptyState } from "@/components/ui";
import { SubgroupCard } from "@/components/subgroups/SubgroupCard";
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
}

const GRID = "grid grid-cols-1 gap-3 sm:grid-cols-2 md:gap-5 lg:grid-cols-3";

/**
 * @brief Group tile mosaic.
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
}: GroupMosaicProps) {
  if (error) {
    return (
      <EmptyState
        title="Couldn't load groups"
        description={String(error)}
        action={
          <Button variant="secondary" onClick={() => window.location.reload()}>
            Retry
          </Button>
        }
      />
    );
  }
  if (isLoading) {
    return (
      <div className={GRID} role="status" aria-label="Loading groups">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height={i % 5 === 0 ? 360 : 240} />
        ))}
      </div>
    );
  }
  if (data.length === 0) {
    return (
      <EmptyState
        title="No groups match"
        description="Try a different filter or start a new circle."
        action={<Button onClick={onCreate}>New group</Button>}
      />
    );
  }

  return (
    <div className={`${GRID} [grid-auto-flow:dense]`}>
      {data.map((g, idx) => {
        const anchor = idx % 5 === 0;
        return (
          <motion.div
            key={g.id}
            layout
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.42,
              ease: [0.22, 1, 0.36, 1],
              delay: Math.min(idx * 0.025, 0.32),
            }}
            className={anchor ? "flex sm:col-span-2" : "flex"}
          >
            <div className="flex-1">
              <SubgroupCard
                subgroup={g}
                anchor={anchor}
                isMember={!!g.my_role}
                onSelect={onSelect}
                onJoin={onJoin}
                onLeave={onLeave}
                busy={joinBusy === g.slug || leaveBusy === g.slug}
              />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

export default GroupMosaic;
