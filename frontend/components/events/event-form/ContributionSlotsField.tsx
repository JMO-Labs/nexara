"use client";
/**
 * @file components/events/event-form/ContributionSlotsField.tsx
 * @brief Editor for an event's contribution slots (title + quantity needed).
 */
import { Plus, Trash2 } from "lucide-react";
import { Button, Input } from "@/components/ui";
import type { ContributionSlot } from "@/lib/api/events";

export interface ContributionSlotsFieldProps {
  value: ContributionSlot[];
  onChange: (next: ContributionSlot[]) => void;
}

/**
 * @brief Whether a quantity is a valid slot size.
 * @param n quantity to check
 * @return true for integers >= 1
 */
export const isValidQuantity = (n: number): boolean =>
  Number.isInteger(n) && n >= 1;

/**
 * @brief List of editable slots with add/remove controls.
 * @param props value and change handler
 * @return fieldset element
 */
export function ContributionSlotsField({
  value,
  onChange,
}: ContributionSlotsFieldProps) {
  const patch = (i: number, p: Partial<ContributionSlot>) =>
    onChange(value.map((s, j) => (j === i ? { ...s, ...p } : s)));

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-1.5 text-sm font-semibold">
        Contribution slots
      </legend>
      {value.map((s, i) => (
        <div key={s.id ?? `new-${i}`} className="flex items-end gap-2">
          <div className="flex-1">
            <Input
              label={`Slot ${i + 1} title`}
              value={s.title}
              onChange={(e) => patch(i, { title: e.target.value })}
            />
          </div>
          <div className="w-28">
            <Input
              label={`Slot ${i + 1} quantity needed`}
              type="number"
              min={1}
              step={1}
              value={s.quantity_needed || ""}
              aria-invalid={!isValidQuantity(s.quantity_needed)}
              onChange={(e) =>
                patch(i, { quantity_needed: Number(e.target.value) })
              }
            />
          </div>
          <Button
            type="button"
            variant="ghost"
            aria-label={`Remove slot ${i + 1}`}
            onClick={() => onChange(value.filter((_, j) => j !== i))}
          >
            <Trash2 className="size-4" aria-hidden="true" />
          </Button>
        </div>
      ))}
      <div>
        <Button
          type="button"
          variant="ghost"
          onClick={() =>
            onChange([
              ...value,
              {
                id: null,
                title: "",
                quantity_needed: 1,
                quantity_claimed: 0,
                claimed_by: [],
              },
            ])
          }
        >
          <Plus className="size-4" aria-hidden="true" /> Add slot
        </Button>
      </div>
    </fieldset>
  );
}

export default ContributionSlotsField;
