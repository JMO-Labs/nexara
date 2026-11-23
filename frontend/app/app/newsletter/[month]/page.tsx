/**
 * @file app/app/newsletter/[month]/page.tsx
 * @brief Printable monthly newsletter for YYYY-MM (print the page or save as PDF).
 */
"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { EmptyState } from "@/components/ui";
import {
  NewsletterView,
  shiftMonth,
} from "@/components/newsletter/NewsletterView";
import { useFeature } from "@/hooks/useFeature";
import { getNewsletter } from "@/lib/api/newsletter";
import { useSession } from "@/stores/session";

/** @return YYYY-MM for now in the browser's zone */
function nowMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function NewsletterRoute({
  params,
}: {
  params: Promise<{ month: string }>;
}) {
  const { month } = use(params);
  const on = useFeature("newsletter");
  const admin = useSession((s) => s.user?.role === "admin");
  const { data, isError, isPending } = useQuery({
    queryKey: ["newsletter", month],
    queryFn: () => getNewsletter(month),
    enabled: on,
    retry: false,
  });
  if (!on) return null;
  if (isError)
    return (
      <EmptyState
        title="No newsletter for this month"
        description="Pick a month between when your community started and today."
      />
    );
  if (isPending || !data) return <p className="text-muted">Loading</p>;
  return (
    <NewsletterView
      data={data}
      admin={admin}
      canNext={shiftMonth(month, 1) <= nowMonth()}
      canPrev
    />
  );
}
