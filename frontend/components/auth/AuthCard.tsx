/**
 * @file components/auth/AuthCard.tsx
 * @brief Shared brand header + glass panel container for auth form pages.
 */
import type { ReactNode } from "react";
import { BrandLockup } from "@/components/brand/Logo";

/**
 * @brief Glass panel with brand lockup, title and optional subtitle.
 * @param title heading text
 * @param subtitle optional line under the heading
 * @param children form content
 * @return auth card
 */
export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div
      data-auth-card-root
      className="mx-auto flex w-full max-w-[400px] flex-col gap-4"
    >
      <div className="flex justify-center">
        <BrandLockup name="Nexara" size={40} />
      </div>
      <div className="glass flex flex-col gap-6 rounded-[32px] p-6 md:p-8">
        <div>
          <h1 className="text-3xl font-medium tracking-tight">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
        </div>
        {children}
      </div>
    </div>
  );
}
