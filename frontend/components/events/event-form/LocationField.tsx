"use client";
/**
 * @file components/events/event-form/LocationField.tsx
 * @brief Location input with debounced geocode suggestions (combobox).
 */
import * as React from "react";
import { Input } from "@/components/ui";
import { useUserLocation } from "@/hooks/useUserLocation";
import { geocodeSearch, type GeocodeResult } from "@/lib/api/geocode";

export interface LocationFieldProps {
  value: string;
  onChange: (next: string, coords: { lat: number; lon: number } | null) => void;
}

/**
 * @brief Free-text location with suggestion list; picking one sets coords.
 * @param props value and change handler
 * @return field element
 */
export function LocationField({ value, onChange }: LocationFieldProps) {
  const userLoc = useUserLocation();
  const [options, setOptions] = React.useState<GeocodeResult[]>([]);
  const [shown, setShown] = React.useState(false);
  const listId = React.useId();

  React.useEffect(() => {
    const q = value.trim();
    if (!shown || q.length < 2) {
      setOptions([]);
      return;
    }
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      try {
        setOptions(
          await geocodeSearch(q, {
            bias: userLoc ? { lat: userLoc.lat, lon: userLoc.lon } : undefined,
            signal: ctrl.signal,
          }),
        );
      } catch {
        setOptions([]);
      }
    }, 250);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [value, shown, userLoc]);

  return (
    <div className="relative">
      <Input
        label="Location"
        role="combobox"
        aria-expanded={shown && options.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        value={value}
        placeholder="Address, place, or venue"
        hint="Suggestions via Photon · © OpenStreetMap contributors"
        onChange={(e) => {
          setShown(true);
          onChange(e.target.value, null);
        }}
        onKeyDown={(e) => e.key === "Escape" && setShown(false)}
      />
      {shown && options.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="bg-surface absolute z-10 mt-1 max-h-70 w-full overflow-auto rounded-xl border border-current/30 shadow-lg"
        >
          {options.map((o) => (
            <li
              key={o.osm_id ?? `${o.label}@${o.lat},${o.lon}`}
              role="option"
              aria-selected={false}
            >
              <button
                type="button"
                className="hover:bg-bg w-full px-3 py-2 text-left text-sm"
                onClick={() => {
                  setShown(false);
                  onChange(o.label, { lat: o.lat, lon: o.lon });
                }}
              >
                {o.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default LocationField;
