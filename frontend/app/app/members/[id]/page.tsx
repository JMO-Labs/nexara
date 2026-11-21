/**
 * @file app/app/members/[id]/page.tsx
 * @brief Member profile route.
 */
"use client";

import { useParams } from "next/navigation";
import { MemberProfile } from "@/components/members/MemberProfile";

/** @brief Member profile page. */
export default function MemberProfilePage() {
  const params = useParams();
  return <MemberProfile userId={params.id as string} />;
}
