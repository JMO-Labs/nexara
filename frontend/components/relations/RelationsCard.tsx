"use client";
/**
 * @file components/relations/RelationsCard.tsx
 * @brief Profile About card for family and friends: the member's confirmed
 *        relations, plus (on your own profile) requests and an add button.
 */
import * as React from "react";
import Link from "next/link";
import { Plus, Users, X } from "lucide-react";
import { Button } from "@/components/ui";
import { IconButton } from "@/components/ui/IconButton";
import { Panel } from "@/components/ui/page";
import { useFeature } from "@/hooks/useFeature";
import { useRelationActions, useRelations } from "@/hooks/useRelations";
import { formatApiError } from "@/lib/api/errors";
import type { Relation } from "@/lib/api/relations";
import { useToasts } from "@/stores/toasts";
import { AddRelationDialog } from "./AddRelationDialog";
import { RelationRequests } from "./RelationRequests";

function Row({ r, isSelf }: { r: Relation; isSelf: boolean }) {
  const { remove } = useRelationActions();
  const p = r.person;
  const pending = r.status === "pending";
  const name = p.username ? (
    <Link href={`/app/u/${p.username}`} className="hover:underline">
      {p.name}
    </Link>
  ) : (
    p.name
  );
  return (
    <li className="flex min-h-9 items-center gap-2 text-sm">
      <span className="min-w-0 flex-1 break-words">
        {name} <span className="text-muted">· {r.display}</span>
        {p.memorial && <span className="text-muted"> · remembered</span>}
        {pending && <span className="text-muted"> · waiting to confirm</span>}
      </span>
      {isSelf && (
        <IconButton
          size="sm"
          variant="ghost"
          aria-label={
            pending ? `Cancel request to ${p.name}` : `Remove ${p.name}`
          }
          onClick={() =>
            remove.mutate(r.id, {
              onError: (e) =>
                useToasts
                  .getState()
                  .push({ variant: "danger", message: formatApiError(e) }),
            })
          }
        >
          <X className="size-4" aria-hidden />
        </IconButton>
      )}
    </li>
  );
}

/**
 * @param props profile owner id and whether it's the viewer's own profile
 * @return card, or null when the feature is off or there is nothing to show
 */
export function RelationsCard({
  userId,
  isSelf,
}: {
  userId: string;
  isSelf: boolean;
}) {
  const on = useFeature("relations");
  const { data } = useRelations(userId, on);
  const [adding, setAdding] = React.useState(false);
  if (!on) return null;
  const rows = (data ?? []).filter((r) => r.direction !== "incoming");
  if (!isSelf && rows.length === 0) return null;
  return (
    <Panel
      title="Family and friends"
      icon={Users}
      actions={
        isSelf && (
          <Button size="sm" variant="ghost" onClick={() => setAdding(true)}>
            <Plus className="size-4" aria-hidden /> Add
          </Button>
        )
      }
    >
      {rows.length === 0 ? (
        <p className="text-sm text-muted">Link the people who matter to you.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {rows.map((r) => (
            <Row key={r.id} r={r} isSelf={isSelf} />
          ))}
        </ul>
      )}
      {isSelf && <RelationRequests />}
      {isSelf && (
        <AddRelationDialog open={adding} onClose={() => setAdding(false)} />
      )}
    </Panel>
  );
}
