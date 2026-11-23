"use client";
/**
 * @file components/tree/TreeControls.tsx
 * @brief Toolbar: zoom, friends toggle, list view toggle, expand.
 */
import { List, Minus, Network, Plus } from "lucide-react";
import { Button } from "@/components/ui";

export interface TreeControlsProps {
  showFriends: boolean;
  onShowFriends: (v: boolean) => void;
  listView: boolean;
  onListView: (v: boolean) => void;
  onZoom: (delta: number) => void;
  onReset: () => void;
  truncated: boolean;
  onExpand?: () => void;
}

/**
 * @param props toolbar state and handlers
 * @return toolbar element
 */
export function TreeControls(p: TreeControlsProps) {
  return (
    <div
      role="toolbar"
      aria-label="Tree controls"
      className="flex flex-wrap items-center gap-2"
    >
      {!p.listView && (
        <>
          <Button
            size="sm"
            variant="glass"
            aria-label="Zoom out"
            onClick={() => p.onZoom(-0.15)}
          >
            <Minus className="size-4" aria-hidden />
          </Button>
          <Button
            size="sm"
            variant="glass"
            aria-label="Zoom in"
            onClick={() => p.onZoom(0.15)}
          >
            <Plus className="size-4" aria-hidden />
          </Button>
          <Button size="sm" variant="glass" onClick={p.onReset}>
            Reset view
          </Button>
        </>
      )}
      <label className="flex min-h-9 items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={p.showFriends}
          onChange={(e) => p.onShowFriends(e.target.checked)}
          className="size-4 accent-[var(--nx-accent)]"
        />
        Show friends
      </label>
      <Button
        size="sm"
        variant="glass"
        aria-pressed={p.listView}
        onClick={() => p.onListView(!p.listView)}
      >
        {p.listView ? (
          <Network className="size-4" aria-hidden />
        ) : (
          <List className="size-4" aria-hidden />
        )}
        {p.listView ? "Tree view" : "List view"}
      </Button>
      {p.truncated && p.onExpand && (
        <Button size="sm" onClick={p.onExpand}>
          Show more relatives
        </Button>
      )}
    </div>
  );
}
