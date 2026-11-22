/**
 * @file components/auth/AuthCard.tsx
 * @brief Split auth card: brand, title and form on the left; the Aegean
 *        mosaic on the right (hidden on small screens).
 */
import type { ReactNode } from "react";
import { BrandLockup } from "@/components/brand/Logo";
import { AuthArt } from "./AuthArt";

/**
 * @brief Auth page frame.
 * @param title heading text
 * @param subtitle optional line under the heading
 * @param footer optional line under the form (e.g. sign-up link)
 * @param children form content
 * @return auth card
 */
export function AuthCard({
  title,
  subtitle,
  footer,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div
      data-auth-card-root
      className="mx-auto grid w-full overflow-hidden rounded-[32px] bg-surface shadow-[0_30px_80px_-30px_rgb(36_50_61/0.35)] md:min-h-[640px] md:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]"
    >
      <div className="flex flex-col gap-10 p-6 sm:p-10 md:p-14">
        <BrandLockup name="Nexara" size={40} />
        <div className="mx-auto flex w-full max-w-[400px] flex-1 flex-col justify-center gap-8">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight">{title}</h1>
            {subtitle && (
              <p className="mt-2 text-base text-muted">{subtitle}</p>
            )}
          </div>
          {children}
          {footer && <p className="text-center text-sm">{footer}</p>}
        </div>
      </div>
      <div className="hidden md:block">
        <AuthArt />
      </div>
    </div>
  );
}
