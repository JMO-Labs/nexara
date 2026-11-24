/**
 * @file lib/api/onboarding.ts
 * @brief Onboarding wizard endpoints and the admin required-steps setting.
 */
import { apiGet, apiPost, apiPut } from "./client";

export type OnboardingStepId =
  | "profile"
  | "birthday"
  | "contact"
  | "family"
  | "notify"
  | "security";

export interface OnboardingState {
  step: number;
  done: boolean;
  required: OnboardingStepId[];
  steps: OnboardingStepId[];
  prefill: { display_name: string; avatar_url: string | null; email: string };
}

export const getOnboarding = () =>
  apiGet<OnboardingState>("/api/v1/onboarding");
export const putOnboardingStep = (step: number) =>
  apiPut<OnboardingState>("/api/v1/onboarding", { step });
export const completeOnboarding = () =>
  apiPost<OnboardingState>("/api/v1/onboarding/complete");
export const getRequiredSteps = () =>
  apiGet<{ required: OnboardingStepId[] }>("/api/v1/admin/onboarding");
export const putRequiredSteps = (required: OnboardingStepId[]) =>
  apiPut<{ required: OnboardingStepId[] }>("/api/v1/admin/onboarding", {
    required,
  });
