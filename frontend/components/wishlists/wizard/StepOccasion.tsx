"use client";
/**
 * @file components/wishlists/wizard/StepOccasion.tsx
 * @brief Wizard step 1: pick an occasion tile (or name your own) and a title.
 */
import { Input } from "@/components/ui";
import { OCCASIONS, type Occasion } from "@/lib/occasions";
import { cn } from "@/lib/utils";
import { Field } from "./fields";
import type { Draft } from "./draft";

/**
 * @brief Occasion grid and title.
 * @param d draft
 * @param set patch the draft
 * @return step body
 */
export function StepOccasion({
  d,
  set,
}: {
  d: Draft;
  set: (p: Partial<Draft>) => void;
}) {
  return (
    <div className="flex flex-col gap-5">
      <fieldset>
        <legend className="mb-3 text-sm font-medium">
          What&apos;s the occasion?
        </legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          {(Object.keys(OCCASIONS) as Occasion[]).map((o) => {
            const { label, Icon, tint, surprise } = OCCASIONS[o];
            const on = d.occasion === o;
            return (
              <button
                key={o}
                type="button"
                aria-pressed={on}
                onClick={() => set({ occasion: o, hide_claims: surprise })}
                className={cn(
                  "glass-item flex min-h-24 flex-col items-center justify-center gap-2 rounded-[20px] p-3 text-sm outline-none transition-[box-shadow,transform] focus-visible:outline-2 focus-visible:outline-accent",
                  on && "shadow-[inset_0_0_0_2px_var(--nx-accent)]",
                )}
              >
                <span
                  aria-hidden
                  className="grid size-10 place-items-center rounded-full text-white"
                  style={{ background: tint }}
                >
                  <Icon className="size-5" />
                </span>
                {label}
              </button>
            );
          })}
        </div>
      </fieldset>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Name it your way (optional)"
          hint="Shown instead of the occasion, e.g. Grandpa's 80th, Office Secret Santa."
        >
          <Input
            maxLength={60}
            value={d.occasion_label}
            onChange={(e) => set({ occasion_label: e.target.value })}
          />
        </Field>
        <Field label="List title">
          <Input
            required
            maxLength={120}
            placeholder="Biscuit turns 5"
            value={d.title}
            onChange={(e) => set({ title: e.target.value })}
          />
        </Field>
      </div>
    </div>
  );
}
