"use client";
/**
 * @file components/settings/GravatarEmailInput.tsx
 * @brief Private email used only for the Gravatar picture (saves on blur).
 */
import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Input } from "@/components/ui";
import { useUserSettings } from "@/hooks/useSettings";
import { updateProfile } from "@/lib/api/settings";
import { formatApiError } from "@/lib/api/errors";
import { qk } from "@/lib/query-keys";

interface Props {
  /** Login email, shown as the placeholder. */
  loginEmail?: string;
  /** Disable while an uploaded photo is in use. */
  disabled?: boolean;
}

/** @return email input under the Gravatar switch */
export function GravatarEmailInput({ loginEmail, disabled }: Props) {
  const qc = useQueryClient();
  const { data } = useUserSettings();
  const saved = data?.gravatar_email ?? "";
  const [value, setValue] = useState(saved);
  const [error, setError] = useState<string>();
  useEffect(() => setValue(saved), [saved]);
  const save = useMutation({
    mutationFn: (v: string) => updateProfile({ gravatar_email: v }),
    onSuccess: () => {
      setError(undefined);
      qc.invalidateQueries({ queryKey: qk.settings.profile() });
      qc.invalidateQueries({ queryKey: qk.auth.me() });
    },
    onError: (e) => setError(formatApiError(e)),
  });
  return (
    <div className="mt-3">
      <Input
        type="email"
        aria-label="Gravatar email"
        placeholder={loginEmail}
        value={value}
        disabled={disabled || save.isPending}
        error={error}
        onChange={(e) => setValue(e.target.value)}
        onBlur={() => {
          if (value.trim() !== saved) save.mutate(value.trim());
        }}
      />
      <p className="mt-1 text-xs text-muted">
        Use a different email for your Gravatar picture. Only you see this.
      </p>
    </div>
  );
}
