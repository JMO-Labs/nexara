"use client";
/**
 * @file components/home/tiles/WeatherTile.tsx
 * @brief Weather tile: your city, saved places and pinned people (city
 *        level, only when their location is visible to you). Each row
 *        expands to a 5-day outlook. Add places by search.
 */
import * as React from "react";
import { CloudSun, Plus, X } from "lucide-react";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { Avatar } from "@/components/ui/Avatar";
import {
  useTempUnit,
  useWeatherBoard,
  useWeatherPlaces,
} from "@/hooks/useWeather";
import type { BoardItem } from "@/lib/api/weather";
import { geocodeSearch, type GeocodeResult } from "@/lib/api/geocode";
import { describe, temp, type TempUnit } from "@/lib/weather";

const dayName = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, {
    weekday: "short",
  });

function Row({
  item,
  unit,
  onRemove,
}: {
  item: BoardItem;
  unit: TempUnit;
  onRemove?: () => void;
}) {
  const fc = item.forecast;
  const { label, Icon } = describe(
    fc?.current.code ?? null,
    fc?.current.is_day ?? true,
  );
  const today = fc?.daily[0];
  return (
    <li className="glass-item rounded-[20px]">
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center gap-3 rounded-[20px] p-2 pr-3 outline-none focus-visible:outline-2 focus-visible:outline-accent [&::-webkit-details-marker]:hidden">
          {item.kind === "place" ? (
            <span className="grid size-8 place-items-center rounded-full bg-[color-mix(in_srgb,var(--nx-blue)_18%,transparent)]">
              <CloudSun className="size-4" aria-hidden />
            </span>
          ) : (
            <Avatar
              size="sm"
              name={item.label}
              src={item.avatar_url ?? undefined}
            />
          )}
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium">
              {item.kind === "self" ? "You" : item.label}
            </span>
            {item.place && (
              <span className="block truncate text-xs text-[var(--nx-muted)]">
                {item.place}
              </span>
            )}
          </span>
          {fc ? (
            <span className="flex items-center gap-2">
              <Icon className="size-5" aria-label={label} />
              <span className="text-lg font-semibold tabular-nums">
                {temp(fc.current.temp_c, unit)}
              </span>
              {today && (
                <span className="text-xs text-[var(--nx-muted)] tabular-nums">
                  {temp(today.max_c, unit)}/{temp(today.min_c, unit)}
                </span>
              )}
            </span>
          ) : (
            <span className="text-xs text-[var(--nx-muted)]">Unavailable</span>
          )}
        </summary>
        {fc && (
          <div className="flex items-center gap-1 px-2 pb-2">
            <ul
              className="grid flex-1 grid-cols-5 gap-1 text-center text-xs"
              aria-label={`5-day outlook for ${item.label}`}
            >
              {fc.daily.slice(1, 6).map((d) => {
                const w = describe(d.code);
                return (
                  <li
                    key={d.date}
                    className="flex flex-col items-center gap-0.5"
                  >
                    <span className="text-[var(--nx-muted)]">
                      {dayName(d.date)}
                    </span>
                    <w.Icon className="size-4" aria-label={w.label} />
                    <span className="tabular-nums">{temp(d.max_c, unit)}</span>
                    <span className="text-[var(--nx-muted)] tabular-nums">
                      {temp(d.min_c, unit)}
                    </span>
                  </li>
                );
              })}
            </ul>
            {onRemove && (
              <button
                type="button"
                onClick={onRemove}
                aria-label={`Remove ${item.label}`}
                className="grid size-8 place-items-center rounded-full hover:bg-[color-mix(in_srgb,var(--nx-ink)_8%,transparent)]"
              >
                <X className="size-4" aria-hidden />
              </button>
            )}
          </div>
        )}
      </details>
    </li>
  );
}

function AddPlace({ onDone }: { onDone: () => void }) {
  const { add } = useWeatherPlaces();
  const [q, setQ] = React.useState("");
  const [hits, setHits] = React.useState<GeocodeResult[]>([]);
  React.useEffect(() => {
    if (q.trim().length < 3) return setHits([]);
    const ac = new AbortController();
    const t = setTimeout(() => {
      geocodeSearch(q, { limit: 5, signal: ac.signal }).then(setHits, () => {});
    }, 350);
    return () => {
      clearTimeout(t);
      ac.abort();
    };
  }, [q]);
  return (
    <div className="flex flex-col gap-1">
      <input
        autoFocus
        aria-label="Search for a place"
        placeholder="City or address"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && onDone()}
        className="glass-item h-10 rounded-full px-4 text-sm outline-none focus-visible:outline-2 focus-visible:outline-accent"
      />
      {hits.length > 0 && (
        <ul aria-label="Places" className="flex flex-col">
          {hits.map((h) => (
            <li key={`${h.lat},${h.lon}`}>
              <button
                type="button"
                className="w-full truncate rounded-full px-4 py-1.5 text-left text-sm hover:bg-[color-mix(in_srgb,var(--nx-ink)_8%,transparent)]"
                onClick={() =>
                  add.mutate(
                    {
                      name: h.label.split(",")[0].slice(0, 80),
                      lat: h.lat,
                      lon: h.lon,
                    },
                    { onSuccess: onDone },
                  )
                }
              >
                {h.label}
              </button>
            </li>
          ))}
        </ul>
      )}
      {add.error && (
        <p role="alert" className="px-2 text-xs text-destructive">
          {add.error.message}
        </p>
      )}
    </div>
  );
}

/**
 * @brief Weather tile.
 * @param props open/onToggle from the home page
 * @return HomeTile
 */
export function WeatherTile({ open, onToggle }: TileSlotProps) {
  const { data: items = [], isLoading } = useWeatherBoard();
  const { remove } = useWeatherPlaces();
  const [unit, setUnit] = useTempUnit();
  const [adding, setAdding] = React.useState(false);
  const first = items.find((i) => i.forecast);
  const summary = first
    ? `${first.kind === "self" ? "Home" : first.label} ${temp(first.forecast!.current.temp_c, unit)}`
    : undefined;
  return (
    <HomeTile
      id="weather"
      title="Weather"
      icon={CloudSun}
      href="/app/settings?tab=profile"
      linkLabel="Your location"
      summary={summary}
      open={open}
      onToggle={onToggle}
      className="md:[grid-area:weather] lg:min-h-0 lg:shrink"
    >
      <div className="flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain">
        <div
          className="flex items-center justify-end gap-1 text-xs"
          role="group"
          aria-label="Temperature unit"
        >
          {(["F", "C"] as const).map((u) => (
            <button
              key={u}
              type="button"
              aria-pressed={unit === u}
              onClick={() => setUnit(u)}
              className={`rounded-full px-2.5 py-1 ${unit === u ? "bg-surface-strong text-bg" : "hover:bg-[color-mix(in_srgb,var(--nx-ink)_8%,transparent)]"}`}
            >
              °{u}
            </button>
          ))}
        </div>
        {isLoading ? null : items.length === 0 && !adding ? (
          <p className="py-2 text-center text-sm text-[var(--nx-muted)]">
            Add your location in your profile, or save a place.
          </p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {items.map((i) => (
              <Row
                key={i.id}
                item={i}
                unit={unit}
                onRemove={
                  i.kind === "place" ? () => remove.mutate(i.id) : undefined
                }
              />
            ))}
          </ul>
        )}
        {adding ? (
          <AddPlace onDone={() => setAdding(false)} />
        ) : (
          items.filter((i) => i.kind === "place").length < 8 && (
            <button
              type="button"
              onClick={() => setAdding(true)}
              className="flex items-center gap-1.5 self-start rounded-full px-3 py-1.5 text-sm hover:bg-[color-mix(in_srgb,var(--nx-ink)_8%,transparent)]"
            >
              <Plus className="size-4" aria-hidden /> Add a place
            </button>
          )
        )}
      </div>
    </HomeTile>
  );
}
