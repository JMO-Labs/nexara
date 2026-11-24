"use client";
/**
 * @file components/onboarding/steps/NotifyStep.tsx
 * @brief Wizard step 5: turn on push notifications for this device.
 */
import { PushDevices } from "@/components/settings/PushDevices";

export function NotifyStep() {
  return <PushDevices />;
}
