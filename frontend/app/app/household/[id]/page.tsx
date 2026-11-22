/**
 * @file app/app/household/[id]/page.tsx
 * @brief Household member / pet page route.
 */
"use client";

import { useParams } from "next/navigation";
import { HouseholdPage } from "@/components/household/HouseholdPage";

/** @brief Household member page. */
export default function HouseholdMemberPage() {
  const params = useParams();
  return <HouseholdPage id={params.id as string} />;
}
