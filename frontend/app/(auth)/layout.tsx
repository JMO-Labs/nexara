/**
 * @file app/(auth)/layout.tsx
 * @brief Auth shell: full-page split layout (AuthCard fills the viewport).
 */
import { Suspense, type ReactNode } from "react";
import { ToastRoot } from "@/components/ui/Toast";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-dvh bg-surface text-ink">
      <div className="min-h-dvh">
        {/* pages read useSearchParams(); required for static prerender */}
        <Suspense>{children}</Suspense>
      </div>
      <ToastRoot />
    </main>
  );
}
