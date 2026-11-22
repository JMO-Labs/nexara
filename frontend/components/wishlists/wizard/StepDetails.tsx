"use client";
/**
 * @file components/wishlists/wizard/StepDetails.tsx
 * @brief Wizard step 3: dates, money (currency, budget guidance, event
 *        budget, per-giver cap), surprise setting, registries, visibility.
 */
import { Plus, X } from "lucide-react";
import { Button, IconButton, Input, Switch, Textarea } from "@/components/ui";
import { CURRENCIES } from "@/lib/money";
import { LEVEL_LABEL, type ProfileLevel } from "@/lib/profile";
import { Field, MoneyInput, selectCls } from "./fields";
import type { Draft } from "./draft";

const REGISTRY_PRESETS = ["Amazon registry", "Target registry", "Zola", "Etsy"];

/**
 * @brief Details step.
 * @param d draft
 * @param set patch the draft
 * @return step body
 */
export function StepDetails({
  d,
  set,
}: {
  d: Draft;
  set: (p: Partial<Draft>) => void;
}) {
  const links = d.registry_links;
  const setLink = (i: number, p: Partial<(typeof links)[number]>) =>
    set({
      registry_links: links.map((l, j) => (j === i ? { ...l, ...p } : l)),
    });
  return (
    <div className="flex flex-col gap-6">
      <section className="grid gap-4 sm:grid-cols-2" aria-label="Dates">
        <Field label="Event date">
          <Input
            type="date"
            value={d.event_date}
            onChange={(e) => set({ event_date: e.target.value })}
          />
        </Field>
        <Field label="Buy by" hint="Gives people time to order and ship.">
          <Input
            type="date"
            value={d.due_by}
            onChange={(e) => set({ due_by: e.target.value })}
          />
        </Field>
      </section>

      <section className="grid gap-4 sm:grid-cols-3" aria-label="Money">
        <Field label="Currency">
          <select
            className={selectCls}
            value={d.currency}
            onChange={(e) => set({ currency: e.target.value })}
          >
            {CURRENCIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </Field>
        <Field label="Suggested spend, from">
          <MoneyInput
            label="Suggested spend minimum"
            currency={d.currency}
            cents={d.budget_min_cents}
            onChange={(c) => set({ budget_min_cents: c })}
          />
        </Field>
        <Field label="to">
          <MoneyInput
            label="Suggested spend maximum"
            currency={d.currency}
            cents={d.budget_max_cents}
            onChange={(c) => set({ budget_max_cents: c })}
          />
        </Field>
        <Field
          label="Limit per person"
          hint="Nobody can claim more than this in total."
        >
          <MoneyInput
            label="Limit per person"
            currency={d.currency}
            cents={d.giver_cap_cents}
            onChange={(c) => set({ giver_cap_cents: c })}
            placeholder="No limit"
          />
        </Field>
        <Field label="Event budget" hint="Your total, to plan against.">
          <MoneyInput
            label="Event budget"
            currency={d.currency}
            cents={d.event_budget_cents}
            onChange={(c) => set({ event_budget_cents: c })}
            placeholder="None"
          />
        </Field>
        <Field label="Who can see it">
          <select
            className={selectCls}
            value={d.visibility}
            onChange={(e) =>
              set({ visibility: e.target.value as ProfileLevel })
            }
          >
            {(Object.keys(LEVEL_LABEL) as ProfileLevel[]).map((l) => (
              <option key={l} value={l}>
                {LEVEL_LABEL[l]}
              </option>
            ))}
          </select>
        </Field>
      </section>

      <label className="glass-item flex items-start justify-between gap-4 rounded-[20px] p-4">
        <span className="flex flex-col gap-0.5">
          <span className="text-sm font-medium">Keep gifts a surprise</span>
          <span className="text-xs text-muted">
            On: the people it&apos;s for never see who is getting what. Off:
            everyone sees who is bringing what, good for reunions and BBQs.
          </span>
        </span>
        <Switch
          aria-label="Keep gifts a surprise"
          checked={d.hide_claims}
          onCheckedChange={(v) => set({ hide_claims: v })}
        />
      </label>

      <section className="flex flex-col gap-2" aria-label="Registries">
        <span className="text-sm font-medium">Registries elsewhere</span>
        {links.map((l, i) => (
          <div
            key={i}
            className="grid grid-cols-[minmax(0,10rem)_minmax(0,1fr)_auto] gap-2"
          >
            <Input
              aria-label={`Registry ${i + 1} name`}
              value={l.label}
              maxLength={60}
              onChange={(e) => setLink(i, { label: e.target.value })}
            />
            <Input
              type="url"
              aria-label={`Registry ${i + 1} link`}
              placeholder="https://www.amazon.com/wedding/registry/..."
              value={l.url}
              onChange={(e) => setLink(i, { url: e.target.value })}
            />
            <IconButton
              variant="ghost"
              size="sm"
              aria-label={`Remove registry ${i + 1}`}
              onClick={() =>
                set({ registry_links: links.filter((_, j) => j !== i) })
              }
            >
              <X className="size-4" aria-hidden />
            </IconButton>
          </div>
        ))}
        {links.length < 10 && (
          <div className="flex flex-wrap gap-2">
            {REGISTRY_PRESETS.map((p) => (
              <Button
                key={p}
                type="button"
                size="sm"
                variant="ghost"
                onClick={() =>
                  set({ registry_links: [...links, { label: p, url: "" }] })
                }
              >
                <Plus className="size-4" aria-hidden /> {p}
              </Button>
            ))}
          </div>
        )}
      </section>

      <Field label="Note for gift-givers">
        <Textarea
          rows={3}
          maxLength={1000}
          placeholder="Sizes, favorite colors, the address to ship to, things to avoid"
          value={d.note}
          onChange={(e) => set({ note: e.target.value })}
        />
      </Field>
    </div>
  );
}
