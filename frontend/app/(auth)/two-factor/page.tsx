"use client";
/**
 * @file app/(auth)/two-factor/page.tsx
 * @brief Completes a two-factor login. Reached only after a sign-in responds
 *        with `requires_2fa: true`. The two_factor_token lives in memory
 *        (pendingTwoFactor store), so a reload loses it and shows the
 *        expired card.
 */
import { safeInternalLink } from "@/lib/safeLink";
import { useState } from "react";
import { useIsClient } from "@/hooks/useIsClient";
import { usePendingTwoFactor } from "@/stores/pendingTwoFactor";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Input, Button } from "@/components/ui";
import { AuthCard } from "@/components/auth/AuthCard";
import { verifyTwoFactorLogin } from "@/lib/api/auth";
import { authenticateWithPasskey, passkeysAvailable } from "@/lib/passkeys";
import { completeLogin } from "@/lib/auth/flow";
import { formatApiError } from "@/lib/api/errors";

const Schema = z.object({
  code: z
    .string()
    .transform((v) => v.replace(/[\s-]/g, ""))
    .pipe(
      z
        .string()
        .min(6, "Enter the 6-digit code")
        .max(8, "Codes are 6–8 characters"),
    ),
});
type FormData = z.infer<typeof Schema>;

export default function TwoFactorPage() {
  const router = useRouter();
  const params = useSearchParams();
  const isClient = useIsClient();
  const token = usePendingTwoFactor((s) => s.token);
  const pending = usePendingTwoFactor((s) => s.methods);
  const next = safeInternalLink(params.get("next")) ?? "/app";
  const canPasskey = isClient && passkeysAvailable();
  const hasPasskey = pending.includes("passkey") && canPasskey;
  const codeMethods = pending.includes("totp") || pending.includes("recovery");
  // Passkey-only over plain HTTP: no usable method on this page.
  const passkeyBlocked =
    pending.includes("passkey") && !codeMethods && !canPasskey;
  // Never leave the card empty: fall back to the code form.
  const hasCode = !passkeyBlocked && (codeMethods || !hasPasskey);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    mode: "onTouched",
    defaultValues: { code: "" },
  });

  if (!isClient) return null;
  if (!token) {
    return (
      <AuthCard
        title="Two-factor session expired"
        subtitle="Your sign-in session was lost (for example after a reload). Sign in again to continue."
      >
        <Link
          href="/login"
          className="inline-flex min-h-11 items-center text-muted underline-offset-4 hover:text-ink underline"
        >
          Back to sign-in
        </Link>
      </AuthCard>
    );
  }

  const onSubmit = async (data: FormData) => {
    setError(null);
    try {
      const resp = await verifyTwoFactorLogin(token, data.code.trim());
      await completeLogin(resp);
      router.replace(next);
    } catch (e) {
      setError(formatApiError(e, "Code rejected."));
    }
  };

  const signInWithPasskey = async () => {
    setError(null);
    try {
      const resp = await authenticateWithPasskey({ pendingToken: token });
      await completeLogin(resp);
      router.replace(next);
    } catch (e) {
      setError(formatApiError(e, "Passkey not accepted."));
    }
  };

  return (
    <AuthCard
      title="Two-factor verification"
      subtitle={
        passkeyBlocked
          ? "Your account signs in with a passkey."
          : hasCode
            ? "Enter the 6-digit code from your authenticator app, or a recovery code."
            : "Confirm it is you with your passkey."
      }
    >
      {error && (
        <p
          role="alert"
          className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error}
        </p>
      )}
      {passkeyBlocked && (
        <>
          <p role="status" className="text-sm">
            Passkeys need a secure (HTTPS) connection. Open the site over HTTPS
            or ask an admin to reset your 2FA.
          </p>
          <Link
            href="/login"
            className="inline-flex min-h-11 items-center text-muted underline-offset-4 hover:text-ink underline"
          >
            Back to sign-in
          </Link>
        </>
      )}
      {hasCode && (
        <form
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          className="flex flex-col gap-4"
        >
          <Input
            label="Code"
            autoFocus={hasCode}
            autoComplete="one-time-code"
            inputMode="text"
            autoCapitalize="characters"
            spellCheck={false}
            error={formState.errors.code?.message}
            disabled={formState.isSubmitting}
            {...register("code")}
          />
          <Button type="submit" size="lg" loading={formState.isSubmitting}>
            Verify
          </Button>
        </form>
      )}
      {hasPasskey && passkeysAvailable() && (
        <Button
          type="button"
          size="lg"
          variant={hasCode ? "ghost" : "primary"}
          onClick={signInWithPasskey}
        >
          Use a passkey
        </Button>
      )}
    </AuthCard>
  );
}
