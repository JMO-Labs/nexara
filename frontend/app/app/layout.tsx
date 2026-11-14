/**
 * @file app/app/layout.tsx
 * @brief Authenticated subtree (/app/**). Real auth gating happens
 *        client-side inside Shell; proxy.ts provides a soft hint redirect.
 */
import { Suspense, type ReactNode } from "react";
import { PageTransition } from "@/components/layout/PageTransition";
import { Shell } from "@/components/layout/Shell";
import { ToastBridge } from "@/components/notifications/ToastBridge";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Shell>
        {/* pages read useSearchParams(); required for static prerender */}
        <PageTransition>
          <Suspense>{children}</Suspense>
        </PageTransition>
      </Shell>
      <ToastBridge />
    </>
  );
}
