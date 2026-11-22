"use client";
/**
 * @file components/home/tiles/PeopleTile.tsx
 * @brief People tile: member, family and pet birthdays / gotcha days in the
 *        next 14 days, then who is online.
 */
import Link from "next/link";
import { Cake, PawPrint, Users } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { useHomePeople } from "@/hooks/useHomePeople";
import { useCelebrations } from "@/hooks/useHousehold";
import { HouseholdAvatar } from "@/components/household/HouseholdCards";

const when = (d: number) =>
  d === 0 ? "Today" : d === 1 ? "Tomorrow" : `In ${d} days`;

/**
 * @brief People tile.
 * @param props open/onToggle from the home page
 * @return HomeTile
 */
export function PeopleTile({ open, onToggle }: TileSlotProps) {
  const people = useHomePeople().data?.items ?? [];
  const family = useCelebrations().data ?? [];
  const bdays = [
    ...people
      .filter((p) => p.birthday_in_days != null)
      .map((p) => ({
        key: p.user_id,
        name: p.display_name,
        href: `/app/members/${p.user_id}`,
        days: p.birthday_in_days!,
        gotcha: false,
        avatar: (
          <Avatar
            src={p.avatar_url ?? undefined}
            name={p.display_name}
            size="sm"
          />
        ),
      })),
    ...family.map((c) => ({
      key: `${c.member.id}-${c.occasion}`,
      name: c.member.name,
      href: `/app/household/${c.member.id}`,
      days: c.in_days,
      gotcha: c.occasion === "gotcha_day",
      avatar: <HouseholdAvatar m={c.member} className="size-8" />,
    })),
  ].sort((a, b) => a.days - b.days);
  const online = people.filter((p) => p.online);
  const first = bdays[0];
  const summary = first
    ? `${first.name.split(" ")[0]}'s ${first.gotcha ? "gotcha day" : "birthday"} ${when(first.days).toLowerCase()}`
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
      className="md:[grid-area:people] lg:max-h-[60%] lg:min-h-0 lg:shrink"
    >
      <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
        {bdays.length > 0 && (
          <ul
            aria-label="Upcoming birthdays and gotcha days"
            className="flex flex-col gap-1"
          >
            {bdays.map((b) => (
              <li key={b.key}>
                <Link
                  href={b.href}
                  className="glass-item flex items-center gap-3 rounded-full p-1.5 pr-4"
                >
                  {b.avatar}
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">
                    {b.name}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-[var(--nx-muted)]">
                    {b.gotcha ? (
                      <PawPrint
                        aria-hidden
                        className="size-3.5 text-[var(--nx-red)]"
                      />
                    ) : (
                      <Cake
                        aria-hidden
                        className="size-3.5 text-[var(--nx-red)]"
                      />
                    )}
                    <span className="sr-only">
                      {b.gotcha ? "Gotcha day" : "Birthday"}
                    </span>
                    {when(b.days)}
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
