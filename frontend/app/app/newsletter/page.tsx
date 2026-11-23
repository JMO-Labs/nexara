/**
 * @file app/app/newsletter/page.tsx
 * @brief Sends the member to the current month's newsletter.
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function NewsletterIndex() {
  const router = useRouter();
  useEffect(() => {
    const d = new Date();
    const m = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    router.replace(`/app/newsletter/${m}`);
  }, [router]);
  return null;
}
