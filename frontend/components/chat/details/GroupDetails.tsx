"use client";
/**
 * @file components/chat/details/GroupDetails.tsx
 * @brief Details for a group channel: members (online first), next event,
 *        open lists, photos. Empty sections are hidden.
 */
import * as React from "react";
import Link from "next/link";
import { format } from "date-fns";
import { Avatar } from "@/components/ui";
import {
  usePresenceStore,
  watchPresence,
  unwatchPresence,
} from "@/stores/presence";
import type { GroupContext } from "@/lib/api/chatContext";
import { DetailsSection, PhotoGrid } from "./DetailsSection";

/**
 * @brief Watch member presence and return how many are online.
 * @param ids member ids
 */
export function useOnlineCount(ids: string[]): number {
  const key = ids.join(",");
  React.useEffect(() => {
    if (!key) return;
    const list = key.split(",");
    watchPresence(list);
    return () => unwatchPresence(list);
  }, [key]);
  const online = usePresenceStore((s) => s.online);
  return ids.filter((id) => online[id]).length;
}

/**
 * @param ctx group context from the API
 * @return details body
 */
export function GroupDetails({ ctx }: { ctx: GroupContext }) {
  const online = usePresenceStore((s) => s.online);
  const ids = React.useMemo(() => ctx.members.map((m) => m.id), [ctx.members]);
  useOnlineCount(ids);
  const sorted = [...ctx.members].sort(
    (a, b) => Number(!!online[b.id]) - Number(!!online[a.id]),
  );
  return (
    <div className="flex flex-col gap-5">
      <DetailsSection
        title={`${ctx.member_count} ${ctx.member_count === 1 ? "member" : "members"}`}
        show={sorted.length > 0}
      >
        <ul className="flex list-none flex-col gap-1 p-0">
          {sorted.map((m) => (
            <li key={m.id} className="flex items-center gap-2.5 py-1">
              <Avatar
                size="md"
                name={m.display_name}
                src={m.avatar_url ?? undefined}
                userId={m.id}
              />
              <span className="truncate text-sm">{m.display_name}</span>
            </li>
          ))}
        </ul>
      </DetailsSection>
      <DetailsSection title="Next event" show={ctx.next_event !== null}>
        {ctx.next_event && (
          <Link
            href={`/app/events/${ctx.next_event.id}`}
            className="block rounded-2xl bg-[var(--nx-bubble)] px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-accent"
          >
            <span className="block truncate font-medium">
              {ctx.next_event.title}
            </span>
            <span className="text-xs text-muted">
              {format(new Date(ctx.next_event.starts_at), "EEE, MMM d · p")}
            </span>
          </Link>
        )}
      </DetailsSection>
      <DetailsSection title="Open lists" show={ctx.open_lists.length > 0}>
        <ul className="flex list-none flex-col gap-1.5 p-0">
          {ctx.open_lists.map((l) => (
            <li key={l.id}>
              <Link
                href={`/app/lists/${l.id}`}
                className="flex items-center justify-between rounded-2xl bg-[var(--nx-bubble)] px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-accent"
              >
                <span className="truncate">{l.title}</span>
                <span className="text-xs text-muted">
                  {l.item_count} {l.item_count === 1 ? "item" : "items"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </DetailsSection>
      <PhotoGrid media={ctx.recent_media} />
    </div>
  );
}
