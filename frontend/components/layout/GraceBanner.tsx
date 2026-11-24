"use client";
/**
 * @file components/layout/GraceBanner.tsx
 * @brief Banner shown while a required 2FA setup is still inside its grace
 *        period. Links to Settings › Security.
 */
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getTwoFactorStatus } from "@/lib/api/twoFactor";

/** @brief Grace-period banner (renders nothing when not applicable). */
export function GraceBanner() {
  const { data } = useQuery({
    queryKey: ["2fa", "status"],
    queryFn: getTwoFactorStatus,
    staleTime: 60_000,
    retry: false,
  });
  if (!data?.required || !data.grace_until || data.totp || data.passkeys > 0)
    return null;
  const date = new Date(data.grace_until).toLocaleDateString();
  return (
    <div
      role="status"
      className="bg-surface px-4 py-2 text-center text-sm print:hidden"
    >
      Your admin requires two-step sign-in. Set it up by {date}.{" "}
      <Link
        href="/app/settings?tab=security"
        className="inline-flex min-h-11 items-center font-medium underline underline-offset-4"
      >
        Go to Security settings
      </Link>
    </div>
  );
}
