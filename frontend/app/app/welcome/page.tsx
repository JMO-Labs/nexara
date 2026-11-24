"use client";
/**
 * @file app/app/welcome/page.tsx
 * @brief Onboarding wizard route. Members who finished onboarding go home,
 *        unless they came back on purpose with ``?resume=1``.
 */
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { WelcomeWizard } from "@/components/onboarding/WelcomeWizard";
import { useOnboarding } from "@/hooks/useOnboarding";

export default function WelcomePage() {
  const router = useRouter();
  const resume = useSearchParams().get("resume") === "1";
  const { data } = useOnboarding();
  const leave = !!data?.done && !resume;
  useEffect(() => {
    if (leave) router.replace("/app");
  }, [leave, router]);
  if (!data || leave) return null;
  return <WelcomeWizard state={data} />;
}
