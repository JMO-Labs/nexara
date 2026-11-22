"use client";
/**
 * @file components/expenses/MemberPicker.tsx
 * @brief Checkbox list of people (keyboard and screen-reader friendly).
 */
import type { UserSummary } from "@/lib/api/users";

/**
 * @brief Pick several members.
 * @param legend group name
 * @param people candidates
 * @param value selected ids
 * @param onChange selection callback
 * @return fieldset
 */
export function MemberPicker({
  legend,
  people,
  value,
  onChange,
}: {
  legend: string;
  people: Pick<UserSummary, "id" | "display_name">[];
  value: string[];
  onChange: (ids: string[]) => void;
}) {
  const toggle = (id: string) =>
    onChange(
      value.includes(id) ? value.filter((v) => v !== id) : [...value, id],
    );
  return (
    <fieldset className="flex flex-col gap-1">
      <legend className="mb-1 text-sm font-medium">{legend}</legend>
      <div className="grid max-h-48 gap-1 overflow-y-auto sm:grid-cols-2">
        {people.map((p) => (
          <label
            key={p.id}
            className="flex min-h-11 cursor-pointer items-center gap-2 rounded-lg px-2 text-sm hover:bg-ink/5"
          >
            <input
              type="checkbox"
              className="size-4 accent-[var(--nx-accent)] focus-visible:outline-2 focus-visible:outline-accent"
              checked={value.includes(p.id)}
              onChange={() => toggle(p.id)}
            />
            {p.display_name}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
