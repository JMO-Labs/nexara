"use client";
/**
 * @file app/app/welcome/page.tsx
 * @brief Onboarding wizard route. Members who finished onboarding go home.
 */
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { WelcomeWizard } from "@/components/onboarding/WelcomeWizard";
import { useOnboarding } from "@/hooks/useOnboarding";

export default function WelcomePage() {
  const router = useRouter();
  const { data } = useOnboarding();
  const done = data?.done;
  useEffect(() => {
    if (done) router.replace("/app");
  }, [done, router]);
  if (!data || data.done) return null;
  return <WelcomeWizard state={data} />;
}
