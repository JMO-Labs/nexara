"use client";
/**
 * @file app/(auth)/callback/page.tsx
 * @brief OAuth callback landing. Backend redirects here with `?code=...`
 *        after exchanging with the IdP; we POST that code to /oauth/exchange
 *        to claim a Nexara session.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { AuthCard } from "@/components/auth/AuthCard";
import { oauthExchange } from "@/lib/api/auth";
import { completeLogin } from "@/lib/auth/flow";
import { formatApiError } from "@/lib/api/errors";

export default function OAuthCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();
  const code = params.get("code");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;
    let cancelled = false;
    (async () => {
      try {
        const resp = await oauthExchange(code);
        if (cancelled) return;
        await completeLogin(resp);
        router.replace("/app");
      } catch (e) {
        if (!cancelled) setError(formatApiError(e, "Sign-in failed."));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, router]);

  const missingCode = !code;

  if (missingCode || error) {
    return (
      <AuthCard title="Sign-in failed">
        <p
          role="alert"
          className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error ?? "Missing OAuth code."}
        </p>
        <Link href="/login" className="underline">
          Back to sign-in
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Finishing sign-in…">
      <div role="status" className="flex items-center gap-3 text-sm opacity-80">
        <Loader2 aria-hidden className="size-5 motion-safe:animate-spin" />
        <span>Trading codes with the identity provider.</span>
      </div>
    </AuthCard>
  );
}
