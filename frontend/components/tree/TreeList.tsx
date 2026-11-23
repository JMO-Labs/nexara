/**
 * @file components/tree/TreeList.tsx
 * @brief Screen-reader friendly nested list form of a tree.
 */
import Link from "next/link";
import type { TreeEdge, TreeNode } from "@/lib/api/tree";
import { buildOutline, lifespan, type OutlineItem } from "@/lib/tree/outline";

function Item({ item }: { item: OutlineItem }) {
  const { node } = item;
  const span = lifespan(node);
  const label = node.link ? (
    <Link
      href={node.link}
      className="font-medium underline-offset-2 hover:underline"
    >
      {node.name}
    </Link>
  ) : (
    <span className="font-medium">{node.name}</span>
  );
  return (
    <li className="my-1">
      {label}
      {node.memorial && (
        <span className="text-muted">
          {" "}
          (remembered{span ? `, ${span}` : ""})
        </span>
      )}
      {item.notes.length > 0 && (
        <span className="text-muted">: {item.notes.join("; ")}</span>
      )}
      {item.children.length > 0 && (
        <ul
          className="ml-4 list-disc pl-4"
          aria-label={`Children of ${node.name}`}
        >
          {item.children.map((c) => (
            <Item key={c.node.id} item={c} />
          ))}
        </ul>
      )}
    </li>
  );
}

/**
 * @param nodes people
 * @param edges relations
 * @param showFriends include friend notes
 * @return nested list
 */
export function TreeList({
  nodes,
  edges,
  showFriends,
}: {
  nodes: TreeNode[];
  edges: TreeEdge[];
  showFriends: boolean;
}) {
  const items = buildOutline(nodes, edges, showFriends);
  return (
    <ul className="m-0 list-disc pl-5 text-sm" aria-label="Family list">
      {items.map((i) => (
        <Item key={i.node.id} item={i} />
      ))}
    </ul>
  );
}
