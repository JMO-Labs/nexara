"use client";
/**
 * @file components/admin/OnboardingSettings.tsx
 * @brief Admin general settings: which onboarding steps new members cannot skip.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Switch } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { formatApiError } from "@/lib/api/errors";
import {
  getRequiredSteps,
  putRequiredSteps,
  type OnboardingStepId,
} from "@/lib/api/onboarding";
import { useToasts } from "@/stores/toasts";

const KEY = ["admin", "onboarding"];
const STEPS: [OnboardingStepId, string][] = [
  ["profile", "Profile photo"],
  ["birthday", "Birthday"],
  ["contact", "Contact details"],
  ["family", "Family or relations"],
];

/** @return panel with one switch per requirable step (saves on change) */
export function OnboardingSettings() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: KEY, queryFn: getRequiredSteps });
  const save = useMutation({
    mutationFn: (r: OnboardingStepId[]) => putRequiredSteps(r),
    onSuccess: (r) => {
      qc.setQueryData(KEY, r);
      useToasts
        .getState()
        .push({ variant: "success", message: "Onboarding saved" });
    },
    onError: (e) =>
      useToasts
        .getState()
        .push({ variant: "danger", message: formatApiError(e) }),
  });
  const required = data?.required ?? [];
  return (
    <Panel as="div" title="Onboarding">
      <p className="text-xs text-muted">
        New members cannot skip these steps. Two-step sign-in is required
        automatically when your security policy covers them.
      </p>
      {STEPS.map(([id, label]) => (
        <div key={id} className="flex items-center justify-between gap-3 py-2">
          <span className="text-sm font-medium">{label}</span>
          <Switch
            aria-label={`Require ${label.toLowerCase()}`}
            checked={required.includes(id)}
            disabled={!data || save.isPending}
            onCheckedChange={(v) =>
              save.mutate(
                v ? [...required, id] : required.filter((r) => r !== id),
              )
            }
          />
        </div>
      ))}
    </Panel>
  );
}
