/**
 * @file app/app/layout.tsx
 * @brief Authenticated subtree (/app/**). Real auth gating happens
 *        client-side inside Shell; proxy.ts provides a soft hint redirect.
 */
import type { ReactNode } from "react";
import { Shell } from "@/components/layout/Shell";
import { PageTransition } from "@/components/layout/PageTransition";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Shell>
      <PageTransition>{children}</PageTransition>
    </Shell>
  );
}
