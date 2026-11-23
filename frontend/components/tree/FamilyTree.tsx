"use client";
/**
 * @file components/tree/FamilyTree.tsx
 * @brief Pan/zoom family tree. Edges are an SVG (role img with a text
 *        summary); people are real links laid over it so they take focus in
 *        row order. A list view gives the same data as nested lists.
 */
import * as React from "react";
import Link from "next/link";
import type { TreeData } from "@/lib/api/tree";
import { layoutTree, NODE_H, NODE_W } from "@/lib/tree/layout";
import { TreeControls } from "./TreeControls";
import { TreeList } from "./TreeList";
import { TreeNode } from "./TreeNode";

interface View {
  x: number;
  y: number;
  k: number;
}
const PAD = 24;
const DASH: Record<string, string | undefined> = {
  friend: "6 5",
  other: "6 5",
  via_family: "2 5",
  sibling: "10 3",
};

/** @brief Plain-text summary used as the SVG label. */
export function summarize(data: TreeData, loose: number): string {
  const people = data.nodes.length;
  const links = data.edges.length;
  return `Family tree with ${people} ${people === 1 ? "person" : "people"} and ${links} ${
    links === 1 ? "link" : "links"
  }${loose ? `; ${loose} not linked yet` : ""}. Use List view for a text version.`;
}

/**
 * @param data nodes and edges
 * @param defaultShowFriends initial friends toggle
 * @param onExpand called by "Show more relatives" when truncated
 * @return tree with controls
 */
export function FamilyTree({
  data,
  defaultShowFriends = false,
  onExpand,
}: {
  data: TreeData;
  defaultShowFriends?: boolean;
  onExpand?: () => void;
}) {
  const [showFriends, setShowFriends] = React.useState(defaultShowFriends);
  const [listView, setListView] = React.useState(false);
  const [view, setView] = React.useState<View>({ x: 0, y: 0, k: 1 });
  const box = React.useRef<HTMLDivElement>(null);
  const drag = React.useRef<{ px: number; py: number; v: View } | null>(null);
  const lay = React.useMemo(
    () => layoutTree(data.nodes, data.edges, { showFriends }),
    [data, showFriends],
  );
  const byId = React.useMemo(
    () => new Map(data.nodes.map((n) => [n.id, n])),
    [data.nodes],
  );
  const placed = React.useMemo(
    () =>
      data.nodes
        .filter((n) => lay.positions[n.id])
        .sort((a, b) => {
          const pa = lay.positions[a.id];
          const pb = lay.positions[b.id];
          return pa.y - pb.y || pa.x - pb.x;
        }),
    [data.nodes, lay],
  );
  const fit = React.useCallback(() => {
    const w = box.current?.clientWidth ?? 0;
    const k = w && lay.width ? Math.min(1, (w - PAD * 2) / lay.width) : 1;
    setView({ x: w ? Math.max(PAD, (w - lay.width * k) / 2) : PAD, y: PAD, k });
  }, [lay.width]);
  React.useEffect(fit, [fit, listView]);

  const zoom = (d: number) =>
    setView((v) => ({
      ...v,
      k: Math.min(2, Math.max(0.3, +(v.k + d).toFixed(2))),
    }));
  React.useEffect(() => {
    const el = box.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      zoom(e.deltaY < 0 ? 0.1 : -0.1);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [listView]);

  const keepVisible = (p: { x: number; y: number }) => {
    const el = box.current;
    if (!el) return;
    el.scrollTo?.(0, 0);
    setView((v) => {
      const left = v.x + p.x * v.k;
      const top = v.y + p.y * v.k;
      let { x, y } = v;
      if (left < 0) x -= left - PAD;
      else if (left + NODE_W * v.k > el.clientWidth)
        x -= left + NODE_W * v.k - el.clientWidth + PAD;
      if (top < 0) y -= top - PAD;
      else if (top + NODE_H * v.k > el.clientHeight)
        y -= top + NODE_H * v.k - el.clientHeight + PAD;
      return { ...v, x, y };
    });
  };

  const edges = data.edges.filter(
    (e) =>
      lay.positions[e.a] &&
      lay.positions[e.b] &&
      (showFriends || (e.kind !== "friend" && e.kind !== "other")),
  );
  const loose = lay.loose.map((id) => byId.get(id)!).filter(Boolean);

  return (
    <div className="flex flex-col gap-3">
      <TreeControls
        showFriends={showFriends}
        onShowFriends={setShowFriends}
        listView={listView}
        onListView={setListView}
        onZoom={zoom}
        onReset={fit}
        truncated={data.truncated}
        onExpand={onExpand}
      />
      {listView ? (
        <TreeList
          nodes={data.nodes}
          edges={data.edges}
          showFriends={showFriends}
        />
      ) : (
        <div
          ref={box}
          className="glass-item relative h-[60vh] min-h-72 touch-none overflow-hidden rounded-2xl"
          onPointerDown={(e) => {
            if ((e.target as HTMLElement).closest("a,[tabindex]")) return;
            drag.current = { px: e.clientX, py: e.clientY, v: view };
          }}
          onPointerMove={(e) => {
            const d = drag.current;
            if (d)
              setView({
                ...d.v,
                x: d.v.x + e.clientX - d.px,
                y: d.v.y + e.clientY - d.py,
              });
          }}
          onPointerUp={() => (drag.current = null)}
          onPointerLeave={() => (drag.current = null)}
        >
          <div
            className="absolute top-0 left-0 origin-top-left"
            style={{
              transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})`,
            }}
          >
            <svg
              role="img"
              aria-label={summarize(data, loose.length)}
              width={Math.max(lay.width, 1)}
              height={Math.max(lay.height, 1)}
              className="absolute top-0 left-0 overflow-visible"
              fill="none"
              stroke="var(--nx-muted)"
              strokeWidth={2}
            >
              {edges.map((e, i) => {
                const a = lay.positions[e.a];
                const b = lay.positions[e.b];
                const d =
                  e.kind === "parent"
                    ? `M${a.x + NODE_W / 2},${a.y + NODE_H} V${(a.y + NODE_H + b.y) / 2} H${b.x + NODE_W / 2} V${b.y}`
                    : `M${a.x + NODE_W / 2},${a.y + NODE_H / 2} L${b.x + NODE_W / 2},${b.y + NODE_H / 2}`;
                return (
                  <path
                    key={`${e.a}-${e.b}-${e.kind}-${i}`}
                    d={d}
                    strokeDasharray={DASH[e.kind]}
                  />
                );
              })}
            </svg>
            <div className="absolute top-0 left-0">
              {placed.map((n) => (
                <TreeNode
                  key={n.id}
                  node={n}
                  x={lay.positions[n.id].x}
                  y={lay.positions[n.id].y}
                  onFocus={() => keepVisible(lay.positions[n.id])}
                />
              ))}
            </div>
          </div>
        </div>
      )}
      {loose.length > 0 && (
        <section aria-label="Not linked yet">
          <h3 className="m-0 mb-1 text-sm font-semibold">Not linked yet</h3>
          <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
            {loose.map((n) => (
              <li key={n.id} className="text-sm">
                {n.link ? (
                  <Link href={n.link} className="underline">
                    {n.name}
                  </Link>
                ) : (
                  n.name
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
