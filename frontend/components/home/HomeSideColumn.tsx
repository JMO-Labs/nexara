"use client";
/**
 * @file components/home/HomeSideColumn.tsx
 * @brief People + Lists side column (lg+): a compact pill rail with live
 *        glances (pinned faces, local temperature, open list items) that
 *        slides the tiles open over the grid on hover/focus (or tap) and
 *        closes when the pointer leaves, so the feed keeps its width. Below lg the wrappers are
 *        `display: contents`, so the tiles sit in the parent grid/accordion.
 */
import * as React from "react";
import { CloudSun, ListChecks, Users } from "lucide-react";
import { PeopleTile } from "@/components/home/tiles/PeopleTile";
import { ListsTile } from "@/components/home/tiles/ListsTile";
import { WeatherTile } from "@/components/home/tiles/WeatherTile";
import type { TileSlotProps } from "@/components/home/HomeTile";
import { Avatar } from "@/components/ui";
import { useHomePeople } from "@/hooks/useHomePeople";
import { useCommunityId } from "@/hooks/useCommunityId";
import { useLists } from "@/hooks/useLists";
import { useTempUnit, useWeatherBoard } from "@/hooks/useWeather";
import { temp } from "@/lib/weather";
import { cn } from "@/lib/utils";

const CLOSE_DELAY = 250;

/**
 * @brief Side column.
 * @param open accordion id currently open (phone)
 * @param onToggle accordion toggle (phone)
 * @return column element
 */
export function HomeSideColumn({
  open,
  onToggle,
}: {
  open: string | null;
  onToggle: TileSlotProps["onToggle"];
}) {
  const [expanded, setExpanded] = React.useState(false);
  const timer = React.useRef<ReturnType<typeof setTimeout>>(undefined);
  const show = () => {
    clearTimeout(timer.current);
    setExpanded(true);
  };
  const hide = () => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setExpanded(false), CLOSE_DELAY);
  };
  React.useEffect(() => () => clearTimeout(timer.current), []);

  const people = useHomePeople().data?.items ?? [];
  const bdays = people.filter((p) => p.birthday_in_days != null).length;
  const faces = [
    ...people.filter((p) => p.favorite),
    ...people.filter((p) => !p.favorite),
  ].slice(0, 3);
  const [unit] = useTempUnit();
  const board = useWeatherBoard().data;
  const here = board?.find((b) => b.kind === "self") ?? board?.[0];
  const c = here?.forecast?.current.temp_c;
  const deg = c != null ? temp(c, unit) : null;
  const todo = (useLists(useCommunityId()).data?.lists ?? []).reduce(
    (n, l) => n + Math.max(0, l.itemCount - l.completedCount),
    0,
  );
  const railBtn =
    "relative flex w-12 flex-col items-center gap-1 rounded-2xl py-2 text-ink outline-none hover:bg-[color-mix(in_srgb,var(--nx-ink)_8%,transparent)] focus-visible:outline-2 focus-visible:outline-accent";
  const glance = "text-[11px] leading-none font-semibold tabular-nums";
  const rule = "h-px w-8 bg-[color-mix(in_srgb,var(--nx-ink)_12%,transparent)]";
  const toggle = () => setExpanded((v) => !v);

  return (
    <div
      data-testid="home-side"
      data-expanded={expanded || undefined}
      onPointerEnter={(e) => e.pointerType === "mouse" && show()}
      onPointerLeave={(e) => e.pointerType === "mouse" && hide()}
      onFocus={show}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) hide();
      }}
      onKeyDown={(e) => e.key === "Escape" && setExpanded(false)}
      className="contents lg:relative lg:flex lg:min-h-0 lg:w-16 lg:[grid-area:side]"
    >
      <nav
        aria-label="People, weather and lists"
        className="glass hidden w-16 flex-col items-center gap-1.5 self-start rounded-[28px] py-2 lg:flex"
      >
        <button
          type="button"
          aria-expanded={expanded}
          aria-label={
            bdays
              ? `People, ${bdays} birthday${bdays === 1 ? "" : "s"} soon`
              : "People"
          }
          title="People"
          onClick={toggle}
          className={railBtn}
        >
          <Users className="size-5" aria-hidden />
          {faces.length > 0 && (
            <span aria-hidden className="flex flex-col items-center -space-y-2">
              {faces.map((p) => (
                <Avatar
                  key={p.user_id}
                  src={p.avatar_url ?? undefined}
                  name={p.display_name}
                  size="sm"
                  className="ring-2 ring-[var(--nx-glass-solid)]"
                />
              ))}
            </span>
          )}
          {bdays > 0 && (
            <span className="absolute top-0.5 right-0.5 grid size-4 place-items-center rounded-full bg-[var(--nx-red)] text-[10px] font-semibold text-white">
              {bdays}
            </span>
          )}
        </button>
        <span aria-hidden className={rule} />
        <button
          type="button"
          aria-expanded={expanded}
          aria-label={
            deg ? `Weather, ${deg} ${here?.label ?? ""}`.trim() : "Weather"
          }
          title="Weather"
          onClick={toggle}
          className={railBtn}
        >
          <CloudSun className="size-5" aria-hidden />
          {deg && <span className={glance}>{deg}</span>}
        </button>
        <span aria-hidden className={rule} />
        <button
          type="button"
          aria-expanded={expanded}
          aria-label={
            todo ? `Lists, ${todo} open item${todo === 1 ? "" : "s"}` : "Lists"
          }
          title="Lists"
          onClick={toggle}
          className={railBtn}
        >
          <ListChecks className="size-5" aria-hidden />
          {todo > 0 && <span className={glance}>{todo}</span>}
        </button>
      </nav>
      <div
        className={cn(
          "contents lg:absolute lg:top-0 lg:right-0 lg:z-30 lg:flex lg:h-full lg:w-[340px] lg:flex-col lg:gap-[18px] lg:transition-[opacity,transform] lg:duration-200 motion-reduce:lg:transition-none lg:[&>section]:min-h-24 lg:[&>section]:overflow-hidden lg:[&>section]:bg-[var(--nx-glass-solid)] lg:[&>section]:shadow-[0_24px_48px_-20px_rgba(0,0,0,0.6)]",
          expanded
            ? "lg:translate-x-0 lg:opacity-100"
            : "lg:pointer-events-none lg:invisible lg:translate-x-6 lg:opacity-0",
        )}
      >
        <PeopleTile open={open === "people"} onToggle={onToggle} />
        <WeatherTile open={open === "weather"} onToggle={onToggle} />
        <ListsTile open={open === "lists"} onToggle={onToggle} />
      </div>
    </div>
  );
}
