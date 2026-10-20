"use client";
/**
 * @file app/(auth)/magic-link/verify/page.tsx
 * @brief Consumes the magic-link token from the URL, exchanges it for a
 *        session, and forwards the user into the app.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { AuthCard } from "@/components/auth/AuthCard";
import { verifyMagicLink } from "@/lib/api/auth";
import { completeLogin } from "@/lib/auth/flow";
import { formatApiError } from "@/lib/api/errors";

export default function MagicLinkVerifyPage() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const resp = await verifyMagicLink(token);
        if (cancelled) return;
        await completeLogin(resp);
        router.replace("/app");
      } catch (e) {
        if (!cancelled)
          setError(formatApiError(e, "This link is invalid or expired."));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, router]);

  if (!token || error) {
    const message = !token ? "Missing token." : error;
    return (
      <AuthCard title="Sign-in failed">
        <p
          role="alert"
          className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive"
        >
          {message}
        </p>
        <Link href="/magic-link" className="underline">
          Request a new link
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Signing you in…">
      <div role="status" className="flex items-center gap-3 text-sm opacity-80">
        <Loader2 aria-hidden className="size-5 motion-safe:animate-spin" />
        <span>Verifying your link.</span>
      </div>
    </AuthCard>
  );
}
