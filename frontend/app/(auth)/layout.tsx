/**
 * @file app/(auth)/layout.tsx
 * @brief Auth shell: shared AppBackdrop with a top-aligned card; the card lives in AuthCard.
 */
import { Suspense, type ReactNode } from "react";
import { ToastRoot } from "@/components/ui/Toast";
import { AppBackdrop } from "@/components/layout/AppBackdrop";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-dvh items-start justify-center px-4 pt-[12vh] pb-8 text-ink">
      <AppBackdrop />
      <div className="w-full max-w-[400px]">
        {/* pages read useSearchParams(); required for static prerender */}
        <Suspense>{children}</Suspense>
      </div>
      <ToastRoot />
    </main>
  );
}
