"use client";
/**
 * @file components/chat/details/PersonDetails.tsx
 * @brief Details for a direct conversation: presence, local time, birthday,
 *        shared groups and events, photos. Empty sections are hidden.
 */
import Link from "next/link";
import { format } from "date-fns";
import { Avatar } from "@/components/ui";
import { useOnline } from "@/stores/presence";
import type { DmContext } from "@/lib/api/chatContext";
import { inDays, localTime, presenceText } from "../format";
import { DetailsSection, PhotoGrid } from "./DetailsSection";

/**
 * @param ctx DM context from the API
 * @return details body
 */
export function PersonDetails({ ctx }: { ctx: DmContext }) {
  const { peer } = ctx;
  const online = useOnline(peer.id);
  const status = presenceText(online, peer.last_seen_at);
  const clock = peer.local_time_tz ? localTime(peer.local_time_tz) : null;
  const first = peer.display_name.split(" ")[0];
  const bday =
    peer.birthday_in_days !== null && peer.birthday_in_days <= 30
      ? `Birthday ${inDays(peer.birthday_in_days)}`
      : null;
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col items-center gap-1 text-center">
        <Avatar
          size="lg"
          className="size-20 text-2xl"
          name={peer.display_name}
          src={peer.avatar_url ?? undefined}
          userId={peer.id}
        />
        <p className="mt-2 text-base font-semibold">{peer.display_name}</p>
        <p className="text-xs text-muted">@{peer.username}</p>
        {status && <p className="text-sm">{status}</p>}
        {clock && (
          <p className="text-xs text-muted">{`${clock} for ${first}`}</p>
        )}
        {bday && <p className="text-xs text-muted">{bday}</p>}
      </div>
      <DetailsSection title="Shared groups" show={ctx.shared_groups.length > 0}>
        <ul className="flex list-none flex-wrap gap-1.5 p-0">
          {ctx.shared_groups.map((g) => (
            <li key={g.id}>
              <Link
                href={`/app/subgroups/${g.slug}`}
                className="rounded-full bg-[var(--nx-bubble)] px-2.5 py-1 text-xs outline-none focus-visible:outline-2 focus-visible:outline-accent"
              >
                {g.name}
              </Link>
            </li>
          ))}
        </ul>
      </DetailsSection>
      <DetailsSection
        title="Upcoming events together"
        show={ctx.upcoming_events.length > 0}
      >
        <ul className="flex list-none flex-col gap-1.5 p-0">
          {ctx.upcoming_events.map((e) => (
            <li key={e.id}>
              <Link
                href={`/app/events/${e.id}`}
                className="block rounded-2xl bg-[var(--nx-bubble)] px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-accent"
              >
                <span className="block truncate font-medium">{e.title}</span>
                <span className="text-xs text-muted">
                  {format(new Date(e.starts_at), "EEE, MMM d · p")}
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
