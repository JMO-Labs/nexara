"use client";
/**
 * @file components/tree/TreeNode.tsx
 * @brief One person on the tree canvas: a link (or focusable label for
 *        private relatives) with avatar, name and, for remembered people,
 *        muted styling plus dates.
 */
import Link from "next/link";
import { Lock } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { cn } from "@/lib/utils";
import type { TreeNode as Node } from "@/lib/api/tree";
import { lifespan } from "@/lib/tree/outline";
import { NODE_H, NODE_W } from "@/lib/tree/layout";

const BOX =
  "glass-item absolute flex items-center gap-2 rounded-xl px-2 text-left text-sm text-ink outline-offset-2 focus-visible:outline-2 focus-visible:outline-accent";

/**
 * @param node person
 * @param x left edge on the canvas
 * @param y top edge on the canvas
 * @param onFocus called when focused (keeps it in view)
 * @return positioned element
 */
export function TreeNode({
  node,
  x,
  y,
  onFocus,
  isRoot = false,
}: {
  node: Node;
  x: number;
  y: number;
  onFocus?: () => void;
  /** The person the tree is centred on (you, on the family page). */
  isRoot?: boolean;
}) {
  const span = lifespan(node);
  const style = { left: x, top: y, width: NODE_W, height: NODE_H };
  const body =
    node.kind === "private" ? (
      <>
        <Lock className="size-5 shrink-0 text-muted" aria-hidden />
        <span className="min-w-0 truncate italic">{node.name}</span>
      </>
    ) : (
      <>
        <span aria-hidden className="shrink-0">
          <Avatar
            src={node.avatar_url ?? undefined}
            name={node.name}
            size="sm"
          />
        </span>
        <span className="min-w-0">
          <span className="block truncate font-medium">{node.name}</span>
          {isRoot && <span className="block text-xs text-muted">You</span>}
          {node.memorial && (
            <span className="block truncate text-xs text-muted">
              {span ?? "Remembered"}
            </span>
          )}
        </span>
      </>
    );
  const cls = cn(
    BOX,
    node.memorial && "border-dashed opacity-80",
    isRoot && "ring-2 ring-accent",
  );
  if (node.link) {
    return (
      <Link
        href={node.link}
        className={cls}
        style={style}
        onFocus={onFocus}
        aria-label={
          node.memorial
            ? `${node.name}, remembered${span ? `, ${span}` : ""}`
            : node.name
        }
      >
        {body}
      </Link>
    );
  }
  return (
    <span tabIndex={0} className={cls} style={style} onFocus={onFocus}>
      {body}
    </span>
  );
}
