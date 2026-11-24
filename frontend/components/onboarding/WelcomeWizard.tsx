"use client";
/**
 * @file components/onboarding/WelcomeWizard.tsx
 * @brief Guided profile setup: one step at a time with Back, Skip for now
 *        (absent when the step is required), Continue and "Step N of M".
 *        Focus moves to the step heading on every change (WCAG 2.4.3).
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { ApiError, formatApiError } from "@/lib/api/errors";
import {
  completeOnboarding,
  putOnboardingStep,
  type OnboardingState,
  type OnboardingStepId,
} from "@/lib/api/onboarding";
import { ONBOARDING_KEY } from "@/hooks/useOnboarding";
import { BirthdayStep } from "./steps/BirthdayStep";
import { ContactStep } from "./steps/ContactStep";
import { FamilyStep } from "./steps/FamilyStep";
import { NotifyStep } from "./steps/NotifyStep";
import { ProfileStep } from "./steps/ProfileStep";
import { SecurityStep } from "./steps/SecurityStep";

const TITLES: Record<OnboardingStepId, string> = {
  profile: "Your name and photo",
  birthday: "Your birthday",
  contact: "How to reach you",
  family: "Family and pets",
  notify: "Notifications",
  security: "Keep your account safe",
};

/** @param state server wizard state (resume point, required steps, prefill) */
export function WelcomeWizard({ state }: { state: OnboardingState }) {
  const router = useRouter();
  const qc = useQueryClient();
  const steps = state.steps;
  const [i, setI] = React.useState(Math.min(state.step, steps.length - 1));
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const heading = React.useRef<HTMLHeadingElement>(null);
  const first = React.useRef(true);
  React.useEffect(() => {
    if (first.current) first.current = false;
    else heading.current?.focus();
  }, [i]);

  const id = steps[i];
  const required = state.required.includes(id);
  const last = i === steps.length - 1;

  /** Forward moves wait for the server, which refuses to skip a required step. */
  const go = async (next: number) => {
    setError(null);
    try {
      await putOnboardingStep(next);
    } catch (e) {
      if (next > i) {
        setError(formatApiError(e));
        return;
      }
    }
    setI(next);
  };
  const advance = async () => {
    if (!last) return go(i + 1);
    setBusy(true);
    try {
      await completeOnboarding();
      await qc.invalidateQueries({ queryKey: ONBOARDING_KEY });
      router.replace("/app");
    } catch (e) {
      const missing = (e instanceof ApiError && e.details?.missing) as
        | OnboardingStepId[]
        | false;
      setError(formatApiError(e));
      if (missing && missing.length) setI(steps.indexOf(missing[0]));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl py-6">
      <p className="text-sm text-muted" aria-live="polite">
        Step {i + 1} of {steps.length}
      </p>
      <h1
        ref={heading}
        tabIndex={-1}
        className="mb-4 text-2xl font-semibold outline-none"
      >
        {TITLES[id]}
      </h1>
      <Panel as="div">
        {id === "profile" && <ProfileStep prefill={state.prefill} />}
        {id === "birthday" && <BirthdayStep />}
        {id === "contact" && <ContactStep />}
        {id === "family" && <FamilyStep />}
        {id === "notify" && <NotifyStep />}
        {id === "security" && <SecurityStep required={required} />}
      </Panel>
      {error && (
        <p role="alert" className="mt-3 text-sm font-medium text-destructive">
          {error}
        </p>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {i > 0 && (
          <Button variant="ghost" onClick={() => void go(i - 1)}>
            Back
          </Button>
        )}
        <span className="flex-1" />
        {!required && (
          <Button
            variant="ghost"
            disabled={busy}
            onClick={() => void advance()}
          >
            Skip for now
          </Button>
        )}
        <Button disabled={busy} onClick={() => void advance()}>
          {last ? "Finish" : "Continue"}
        </Button>
      </div>
    </div>
  );
}
