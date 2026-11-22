"use client";
/**
 * @file components/events/event-detail/EventForecast.tsx
 * @brief Forecast line for an event's place and day, shown once the day is
 *        within the 16-day forecast window.
 */
import { useForecast, useTempUnit } from "@/hooks/useWeather";
import { describe, temp } from "@/lib/weather";

/** @brief Local YYYY-MM-DD for an ISO timestamp. */
const localDate = (iso: string) => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

/**
 * @brief Event forecast line.
 * @param lat event latitude
 * @param lon event longitude
 * @param startsAt event start (ISO)
 * @return line or null
 */
export function EventForecast({
  lat,
  lon,
  startsAt,
}: {
  lat: number;
  lon: number;
  startsAt: string;
}) {
  const { data } = useForecast(lat, lon);
  const [unit] = useTempUnit();
  const day = data?.daily.find((d) => d.date === localDate(startsAt));
  if (!day) return null;
  const { label, Icon } = describe(day.code);
  return (
    <div className="mb-3 flex items-center gap-2 text-sm">
      <Icon className="size-4" aria-hidden />
      <span>
        Forecast: {label}, {temp(day.max_c, unit)} / {temp(day.min_c, unit)}
        {day.precip ? `, ${day.precip}% chance of rain` : ""}
      </span>
    </div>
  );
}
