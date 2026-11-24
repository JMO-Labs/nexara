"use client";
/**
 * @file components/onboarding/steps/ContactStep.tsx
 * @brief Wizard step 3: phone, contact email, address and location. Each
 *        field saves on blur; visibility pickers default to "Only me".
 */
import * as React from "react";
import { Input } from "@/components/ui";
import { VisibilitySelect } from "@/components/settings/VisibilitySelect";
import { useMyProfile, useUpdateProfile } from "@/hooks/useSettings";
import type { ProfileUpdate } from "@/lib/api/settings";

type Key = "phone" | "contact_email" | "address" | "location";
const FIELDS: [Key, string][] = [
  ["phone", "Phone"],
  ["contact_email", "Contact email"],
  ["address", "Address"],
  ["location", "Location"],
];

export function ContactStep() {
  const { data: me } = useMyProfile();
  const { mutate } = useUpdateProfile();
  const [draft, setDraft] = React.useState<Partial<Record<Key, string>>>({});
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted">
        Only you see these until you choose to share them.
      </p>
      {FIELDS.map(([key, label]) => (
        <div key={key}>
          <label htmlFor={`ob-${key}`} className="text-sm font-medium">
            {label}
          </label>
          <div className="flex items-center gap-2">
            <Input
              id={`ob-${key}`}
              className="min-w-0 flex-1"
              value={draft[key] ?? me?.[key] ?? ""}
              onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
              onBlur={() => {
                const v = draft[key];
                if (v !== undefined && v !== (me?.[key] ?? ""))
                  mutate({ [key]: v.trim() } as ProfileUpdate);
              }}
            />
            <VisibilitySelect field={key} label={label.toLowerCase()} />
          </div>
        </div>
      ))}
    </div>
  );
}
