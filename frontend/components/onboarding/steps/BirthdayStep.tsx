"use client";
/**
 * @file components/onboarding/steps/BirthdayStep.tsx
 * @brief Wizard step 2: birthday (also decides the age group). Saved on blur
 *        and only when complete and plausible: a date input emits half-typed
 *        years (0002, 0020...) that must never reach the server.
 */
import * as React from "react";
import { Input } from "@/components/ui";
import { useMyProfile, useUpdateProfile } from "@/hooks/useSettings";

/** @return whether ``v`` is a full ISO date from 1900 up to today */
export function plausibleBirthday(v: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
  const today = new Date().toISOString().slice(0, 10);
  return v >= "1900-01-01" && v <= today;
}

/**
 * @param onSave receives the in-flight save so the wizard can await it before
 *        leaving the step (Next never races the blur save)
 */
export function BirthdayStep({
  onSave,
}: {
  onSave?: (p: Promise<unknown>) => void;
}) {
  const { data: me } = useMyProfile();
  const { mutateAsync } = useUpdateProfile();
  const [value, setValue] = React.useState<string | null>(null);
  const [error, setError] = React.useState(false);
  const shown = value ?? me?.birthday ?? "";
  const save = () => {
    if (value === null || value === (me?.birthday ?? "") || !value) return;
    const ok = plausibleBirthday(value);
    setError(!ok);
    if (!ok) return;
    const p = mutateAsync({ birthday: value }).catch(() => {});
    onSave?.(p);
  };
  return (
    <div>
      <label htmlFor="ob-birthday" className="text-sm font-medium">
        Birthday
      </label>
      <p className="mb-2 text-xs text-muted">
        Used for birthday reminders and to pick the right age group. Only the
        day and month are shown unless you choose to show the year.
      </p>
      <Input
        id="ob-birthday"
        type="date"
        value={shown}
        min="1900-01-01"
        max={new Date().toISOString().slice(0, 10)}
        aria-invalid={error || undefined}
        aria-describedby={error ? "ob-birthday-err" : undefined}
        onChange={(e) => setValue(e.target.value)}
        onBlur={save}
      />
      {error && (
        <p
          id="ob-birthday-err"
          role="alert"
          className="mt-1 text-xs font-medium text-destructive"
        >
          Enter a date between 1900 and today.
        </p>
      )}
    </div>
  );
}
