"use client";
/**
 * @file components/home/tiles/PeopleTile.tsx
 * @brief People tile: birthdays in the next 14 days, then who is online.
 */
import Link from "next/link";
import { Cake, Users } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { useHomePeople } from "@/hooks/useHomePeople";

const when = (d: number) =>
  d === 0 ? "Today" : d === 1 ? "Tomorrow" : `In ${d} days`;

/**
 * @brief People tile.
 * @param props open/onToggle from the home page
 * @return HomeTile
 */
export function PeopleTile({ open, onToggle }: TileSlotProps) {
  const people = useHomePeople().data?.items ?? [];
  const bdays = people
    .filter((p) => p.birthday_in_days != null)
    .sort((a, b) => a.birthday_in_days! - b.birthday_in_days!);
  const online = people.filter((p) => p.online);
  const summary = bdays[0]
    ? `${bdays[0].display_name.split(" ")[0]}'s birthday ${when(bdays[0].birthday_in_days!).toLowerCase()}`
    : `${online.length} online`;
  return (
    <HomeTile
      id="people"
      title="People"
      icon={Users}
      href="/app/members"
      linkLabel="Directory"
      summary={summary}
      open={open}
      onToggle={onToggle}
      className="md:[grid-area:people] lg:min-h-0 lg:flex-1"
    >
      <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
        {bdays.length > 0 && (
          <ul aria-label="Upcoming birthdays" className="flex flex-col gap-1">
            {bdays.map((p) => (
              <li key={p.user_id}>
                <Link
                  href={`/app/members/${p.user_id}`}
                  className="glass-item flex items-center gap-3 rounded-full p-1.5 pr-4"
                >
                  <Avatar
                    src={p.avatar_url ?? undefined}
                    name={p.display_name}
                    size="sm"
                  />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">
                    {p.display_name}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-[var(--nx-muted)]">
                    <Cake
                      aria-hidden
                      className="size-3.5 text-[var(--nx-red)]"
                    />
                    {when(p.birthday_in_days!)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        <div>
          <p className="mb-2 text-sm text-[var(--nx-muted)]">
            {online.length
              ? `Online now (${online.length})`
              : "Nobody online right now"}
          </p>
          <ul className="flex flex-wrap gap-2">
            {online.map((p) => (
              <li key={p.user_id}>
                <Link
                  href={`/app/members/${p.user_id}`}
                  aria-label={p.display_name}
                >
                  <Avatar
                    src={p.avatar_url ?? undefined}
                    name={p.display_name}
                    size="md"
                  />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </HomeTile>
  );
}
