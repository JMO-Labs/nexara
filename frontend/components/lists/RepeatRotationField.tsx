"use client";
/**
 * @file components/lists/RepeatRotationField.tsx
 * @brief Chore schedule control for a list item: repeat (Never/Daily/Weekly/
 *        Monthly) plus an ordered rotation of people, reordered with up/down
 *        buttons so it works without a mouse.
 */
import { useId, useState } from "react";
import { ArrowDown, ArrowUp, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { IconButton } from "@/components/ui/IconButton";
import { controlClass } from "@/components/ui/Field";
import type { ChoreRepeat } from "@/lib/api/listTypes";

export interface RepeatRotationValue {
  repeat: ChoreRepeat | null;
  rotation: string[];
}

export interface RepeatRotationFieldProps {
  value: RepeatRotationValue;
  onChange: (v: RepeatRotationValue) => void;
  /** People who may be added (id + display name). */
  people: { id: string; name: string }[];
}

const OPTIONS: { value: ChoreRepeat | ""; label: string }[] = [
  { value: "", label: "Never" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

/**
 * @brief Move an element one step; out-of-range moves return the input.
 * @param list ids
 * @param i index to move
 * @param d -1 (up) or 1 (down)
 * @return new array
 */
export function moveItem(list: string[], i: number, d: -1 | 1): string[] {
  const j = i + d;
  if (j < 0 || j >= list.length) return list;
  const out = [...list];
  [out[i], out[j]] = [out[j], out[i]];
  return out;
}

/**
 * @brief Repeat selector and ordered people picker.
 * @param props see RepeatRotationFieldProps
 * @return field group
 */
export function RepeatRotationField({
  value,
  onChange,
  people,
}: RepeatRotationFieldProps) {
  const id = useId();
  const [pick, setPick] = useState("");
  const name = (uid: string) =>
    people.find((p) => p.id === uid)?.name ?? "Former member";
  const addable = people.filter((p) => !value.rotation.includes(p.id));
  const set = (rotation: string[]) => onChange({ ...value, rotation });
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-semibold">Repeat</legend>
      <select
        aria-label="Repeat"
        className={`${controlClass} h-11`}
        value={value.repeat ?? ""}
        onChange={(e) =>
          onChange({
            repeat: (e.target.value || null) as ChoreRepeat | null,
            rotation: e.target.value ? value.rotation : [],
          })
        }
      >
        {OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {value.repeat && (
        <>
          <p id={`${id}-help`} className="text-sm text-muted">
            Takes turns in this order.
          </p>
          <ol aria-describedby={`${id}-help`} className="flex flex-col gap-1">
            {value.rotation.map((uid, i) => (
              <li
                key={uid}
                className="glass-item flex items-center gap-2 rounded-[16px] px-3 py-1.5 text-sm"
              >
                <span className="flex-1">
                  {i + 1}. {name(uid)}
                </span>
                <IconButton
                  size="sm"
                  variant="glass"
                  type="button"
                  aria-label={`Move ${name(uid)} up`}
                  disabled={i === 0}
                  onClick={() => set(moveItem(value.rotation, i, -1))}
                >
                  <ArrowUp aria-hidden className="size-4" />
                </IconButton>
                <IconButton
                  size="sm"
                  variant="glass"
                  type="button"
                  aria-label={`Move ${name(uid)} down`}
                  disabled={i === value.rotation.length - 1}
                  onClick={() => set(moveItem(value.rotation, i, 1))}
                >
                  <ArrowDown aria-hidden className="size-4" />
                </IconButton>
                <IconButton
                  size="sm"
                  variant="glass"
                  type="button"
                  aria-label={`Remove ${name(uid)} from rotation`}
                  onClick={() => set(value.rotation.filter((r) => r !== uid))}
                >
                  <X aria-hidden className="size-4" />
                </IconButton>
              </li>
            ))}
          </ol>
          {addable.length > 0 && (
            <div className="flex gap-2">
              <select
                aria-label="Add person to rotation"
                className={`${controlClass} h-11 flex-1`}
                value={pick}
                onChange={(e) => setPick(e.target.value)}
              >
                <option value="">Choose a person</option>
                {addable.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                variant="secondary"
                disabled={!pick}
                onClick={() => {
                  set([...value.rotation, pick]);
                  setPick("");
                }}
              >
                Add
              </Button>
            </div>
          )}
        </>
      )}
    </fieldset>
  );
}
