/**
 * @file app/(auth)/layout.tsx
 * @brief Auth shell: shared AppBackdrop with a centred split card (AuthCard).
 */
import { Suspense, type ReactNode } from "react";
import { ToastRoot } from "@/components/ui/Toast";
import { AppBackdrop } from "@/components/layout/AppBackdrop";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-dvh items-start justify-center px-4 pt-[8vh] pb-8 text-ink md:items-center md:py-8">
      <AppBackdrop />
      <div className="w-full max-w-[1080px]">
        {/* pages read useSearchParams(); required for static prerender */}
        <Suspense>{children}</Suspense>
      </div>
      <ToastRoot />
    </main>
  );
}
