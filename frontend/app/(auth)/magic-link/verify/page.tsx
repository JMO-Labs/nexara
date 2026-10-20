"use client";
/**
 * @file app/(auth)/magic-link/verify/page.tsx
 * @brief Consumes the magic-link token from the URL, exchanges it for a
 *        session, and forwards the user into the app.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import CircularProgress from "@mui/joy/CircularProgress";
import Stack from "@mui/joy/Stack";
import Alert from "@mui/joy/Alert";
import Typography from "@mui/joy/Typography";
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
        <Alert color="danger" variant="soft">
          {message}
        </Alert>
        <Link href="/magic-link" style={{ textDecoration: "underline" }}>
          Request a new link
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Signing you in…">
      <Stack direction="row" spacing={2} alignItems="center">
        <CircularProgress size="sm" />
        <Typography level="body-md" color="neutral">
          Verifying your link.
        </Typography>
      </Stack>
    </AuthCard>
  );
}
