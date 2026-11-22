"use client";
/**
 * @file components/wishlists/wizard/WishlistWizard.tsx
 * @brief Three-step wishlist builder (occasion, who it's for, details) used
 *        to create a list and to edit one.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Check } from "lucide-react";
import { Button } from "@/components/ui";
import { useWishlistActions } from "@/hooks/useWishlists";
import { useSession } from "@/stores/session";
import type { WishlistDetail } from "@/lib/api/wishlists";
import { cn } from "@/lib/utils";
import { draftError, initialDraft, toInput, type Draft } from "./draft";
import { StepDetails } from "./StepDetails";
import { StepOccasion } from "./StepOccasion";
import { StepRecipients } from "./StepRecipients";

const STEPS = ["Occasion", "Who it's for", "Dates, money and more"];

/**
 * @brief Wishlist wizard.
 * @param list list to edit, or undefined to create
 * @param onDone called after saving (edit) — create navigates to the list
 * @param onCancel cancel handler
 * @return wizard
 */
export function WishlistWizard({
  list,
  onDone,
  onCancel,
}: {
  list?: WishlistDetail;
  onDone?: () => void;
  onCancel: () => void;
}) {
  const router = useRouter();
  const me = useSession((s) => s.user);
  const { create, update } = useWishlistActions();
  const [d, setD] = React.useState<Draft>(() =>
    initialDraft(
      list,
      me ? { kind: "user", ref_id: me.id, label: "Me" } : undefined,
    ),
  );
  const [step, setStep] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);
  const set = (p: Partial<Draft>) => setD((o) => ({ ...o, ...p }));
  const last = step === STEPS.length - 1;
  const heading = React.useRef<HTMLHeadingElement>(null);

  const go = (to: number) => {
    const err = to > step ? draftError(d, step) : null;
    if (err) return setError(err);
    setError(null);
    setStep(to);
    requestAnimationFrame(() => heading.current?.focus());
  };

  const save = () => {
    const err = draftError(d, STEPS.length - 1);
    if (err) return setError(err);
    const onError = (e: unknown) =>
      setError(e instanceof Error ? e.message : "Couldn't save.");
    if (list)
      update.mutate(
        { id: list.id, body: toInput(d) },
        { onSuccess: () => onDone?.(), onError },
      );
    else
      create.mutate(toInput(d), {
        onSuccess: (w) => router.push(`/app/wishlists/${w.id}`),
        onError,
      });
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (last) save();
        else go(step + 1);
      }}
      className="flex flex-col gap-6"
      aria-label={list ? "Edit wishlist" : "New wishlist"}
    >
      <ol className="flex flex-wrap gap-2" aria-label="Steps">
        {STEPS.map((s, i) => (
          <li key={s}>
            <button
              type="button"
              aria-current={i === step ? "step" : undefined}
              onClick={() => (i < step || list ? go(i) : undefined)}
              className={cn(
                "inline-flex h-9 items-center gap-2 rounded-full px-3 text-sm",
                i === step
                  ? "bg-surface-strong text-bg"
                  : "glass-item text-ink",
              )}
            >
              <span
                aria-hidden
                className="grid size-5 place-items-center rounded-full bg-[color-mix(in_srgb,currentColor_15%,transparent)] text-xs"
              >
                {i < step ? <Check className="size-3" /> : i + 1}
              </span>
              {s}
            </button>
          </li>
        ))}
      </ol>
      <h2 ref={heading} tabIndex={-1} className="sr-only">
        Step {step + 1}: {STEPS[step]}
      </h2>
      {step === 0 && <StepOccasion d={d} set={set} />}
      {step === 1 && <StepRecipients d={d} set={set} />}
      {step === 2 && <StepDetails d={d} set={set} />}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="flex flex-wrap justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          onClick={step ? () => go(step - 1) : onCancel}
        >
          {step ? "Back" : "Cancel"}
        </Button>
        {list && !last && (
          <Button
            type="button"
            variant="secondary"
            onClick={save}
            loading={update.isPending}
          >
            Save changes
          </Button>
        )}
        <Button type="submit" loading={create.isPending || update.isPending}>
          {last ? (list ? "Save changes" : "Create wishlist") : "Next"}
        </Button>
      </div>
    </form>
  );
}
