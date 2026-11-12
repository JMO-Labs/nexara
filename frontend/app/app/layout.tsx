/**
 * @file app/app/layout.tsx
 * @brief Authenticated subtree (/app/**). Real auth gating happens
 *        client-side inside Shell; proxy.ts provides a soft hint redirect.
 */
import { Suspense, type ReactNode } from "react";
import { Shell } from "@/components/layout/Shell";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Shell>
      {/* pages read useSearchParams(); required for static prerender */}
      <Suspense>{children}</Suspense>
    </Shell>
  );
}
