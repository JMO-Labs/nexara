"use client";
/**
 * @file components/onboarding/steps/BirthdayStep.tsx
 * @brief Wizard step 2: birthday (also decides the age group).
 */
import * as React from "react";
import { Input } from "@/components/ui";
import { useMyProfile, useUpdateProfile } from "@/hooks/useSettings";

export function BirthdayStep() {
  const { data: me } = useMyProfile();
  const { mutate } = useUpdateProfile();
  const [value, setValue] = React.useState<string | null>(null);
  const shown = value ?? me?.birthday ?? "";
  return (
    <div>
      <label htmlFor="ob-birthday" className="text-sm font-medium">
        Birthday
      </label>
      <p className="mb-2 text-xs text-muted">
        Used for birthday reminders and to pick the right age group.
      </p>
      <Input
        id="ob-birthday"
        type="date"
        value={shown}
        max={new Date().toISOString().slice(0, 10)}
        onChange={(e) => {
          setValue(e.target.value);
          if (e.target.value) mutate({ birthday: e.target.value });
        }}
      />
    </div>
  );
}
