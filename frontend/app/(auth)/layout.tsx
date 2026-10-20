/**
 * @file app/(auth)/layout.tsx
 * @brief Centered auth shell on the bg token; the card lives in AuthCard.
 */
import type { ReactNode } from "react";
import { ToastRoot } from "@/components/ui/Toast";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg px-4 py-8 text-ink">
      <div className="w-full max-w-sm">{children}</div>
      <ToastRoot />
    </main>
  );
}
