"use client";
/**
 * @file lib/lists/fieldTypes/LocationField.tsx
 * @brief Location field (address and coordinates).
 */
import { Input } from "@/components/ui/Input";
import {
  NoConfig,
  type FieldEditProps,
  type FieldType,
  type FieldViewProps,
} from "./base";

interface Loc {
  address?: string;
  lat?: string;
  lng?: string;
}
const loc = (v: unknown): Loc => (v && typeof v === "object" ? (v as Loc) : {});

function View({ value }: FieldViewProps) {
  const l = loc(value);
  if (!l.address && !l.lat && !l.lng) return <span>—</span>;
  return (
    <span>
      {l.address}
      {l.lat && l.lng ? ` (${l.lat}, ${l.lng})` : ""}
    </span>
  );
}

function Edit({ value, onChange }: FieldEditProps) {
  const l = loc(value);
  const set = (p: Loc) => onChange({ ...l, ...p });
  return (
    <div className="flex flex-col gap-2">
      <Input
        aria-label="Address"
        value={l.address ?? ""}
        onChange={(e) => set({ address: e.target.value })}
      />
      <div className="grid grid-cols-2 gap-2">
        <Input
          aria-label="Latitude"
          inputMode="decimal"
          value={l.lat ?? ""}
          onChange={(e) => set({ lat: e.target.value })}
        />
        <Input
          aria-label="Longitude"
          inputMode="decimal"
          value={l.lng ?? ""}
          onChange={(e) => set({ lng: e.target.value })}
        />
      </div>
    </div>
  );
}

/** @brief Location field type (map picker deferred). */
export const LocationField: FieldType = {
  key: "location",
  label: "Location",
  View,
  Edit,
  ConfigEditor: NoConfig,
};
