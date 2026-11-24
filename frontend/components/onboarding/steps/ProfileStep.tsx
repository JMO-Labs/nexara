"use client";
/**
 * @file components/onboarding/steps/ProfileStep.tsx
 * @brief Wizard step 1: display name (prefilled from sign-up / SSO), photo
 *        and pronouns.
 */
import * as React from "react";
import { Input } from "@/components/ui";
import { AvatarPicker } from "@/components/settings/AvatarPicker";
import { useMyProfile, useUpdateProfile } from "@/hooks/useSettings";
import type { OnboardingState } from "@/lib/api/onboarding";

/** @param prefill name/avatar already known from sign-up or SSO */
export function ProfileStep({
  prefill,
}: {
  prefill: OnboardingState["prefill"];
}) {
  const { data: me } = useMyProfile();
  const { mutate } = useUpdateProfile();
  const [name, setName] = React.useState(prefill.display_name);
  const [pronouns, setPronouns] = React.useState<string | null>(null);
  return (
    <div className="space-y-4">
      <AvatarPicker
        name={name || prefill.display_name}
        src={me?.avatar_url ?? prefill.avatar_url}
        onChange={(id) => mutate({ avatar_media_id: id })}
      />
      <div>
        <label htmlFor="ob-name" className="text-sm font-medium">
          Display name
        </label>
        <Input
          id="ob-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onBlur={() => {
            const v = name.trim();
            if (v && v !== me?.display_name) mutate({ display_name: v });
          }}
        />
      </div>
      <div>
        <label htmlFor="ob-pronouns" className="text-sm font-medium">
          Pronouns
        </label>
        <Input
          id="ob-pronouns"
          maxLength={50}
          placeholder="e.g. she/her"
          value={pronouns ?? me?.pronouns ?? ""}
          onChange={(e) => setPronouns(e.target.value)}
          onBlur={() => {
            const v = (pronouns ?? "").trim();
            if (pronouns !== null && v !== (me?.pronouns ?? ""))
              mutate({ pronouns: v });
          }}
        />
      </div>
    </div>
  );
}
