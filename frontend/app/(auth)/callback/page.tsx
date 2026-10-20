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
import CircularProgress from "@mui/joy/CircularProgress";
import Stack from "@mui/joy/Stack";
import Alert from "@mui/joy/Alert";
import Typography from "@mui/joy/Typography";
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
        <Alert color="danger" variant="soft">
          {error ?? "Missing OAuth code."}
        </Alert>
        <Link href="/login" style={{ textDecoration: "underline" }}>
          Back to sign-in
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Finishing sign-in…">
      <Stack direction="row" spacing={2} alignItems="center">
        <CircularProgress size="sm" />
        <Typography level="body-md" color="neutral">
          Trading codes with the identity provider.
        </Typography>
      </Stack>
    </AuthCard>
  );
}
