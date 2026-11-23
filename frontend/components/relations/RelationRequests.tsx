"use client";
/**
 * @file components/relations/RelationRequests.tsx
 * @brief Incoming family and friend requests with Accept / Decline.
 */
import { Button } from "@/components/ui";
import { useRelationActions, useRelationRequests } from "@/hooks/useRelations";
import { formatApiError } from "@/lib/api/errors";
import type { RelationKind } from "@/lib/api/relations";
import { useToasts } from "@/stores/toasts";

const INVERSE: Partial<Record<RelationKind, RelationKind>> = {
  parent: "child",
  child: "parent",
};

/**
 * @brief What the requester says you are to them ("parent").
 * @param kind kind of the requester, seen from you
 * @param label free text for "other"
 * @return lowercase word
 */
export function theirWord(kind: RelationKind, label: string | null): string {
  return label ?? INVERSE[kind] ?? kind;
}

/**
 * @brief Requests list; renders nothing when there are none.
 * @return list or null
 */
export function RelationRequests() {
  const { data } = useRelationRequests();
  const { confirm, remove } = useRelationActions();
  if (!data?.length) return null;
  const fail = (e: unknown) =>
    useToasts
      .getState()
      .push({ variant: "danger", message: formatApiError(e) });
  return (
    <section aria-label="Requests" className="mt-4">
      <h3 className="mb-2 text-sm font-medium">Requests</h3>
      <ul className="flex flex-col gap-2">
        {data.map((r) => (
          <li key={r.id} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="min-w-0 flex-1">
              {r.person.name} says you&apos;re their{" "}
              {theirWord(r.kind, r.label)}
            </span>
            <Button
              size="sm"
              aria-label={`Accept ${r.person.name}`}
              loading={confirm.isPending && confirm.variables === r.id}
              onClick={() => confirm.mutate(r.id, { onError: fail })}
            >
              Accept
            </Button>
            <Button
              size="sm"
              variant="ghost"
              aria-label={`Decline ${r.person.name}`}
              onClick={() => remove.mutate(r.id, { onError: fail })}
            >
              Decline
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
