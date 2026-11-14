"use client";
/**
 * @file app/(auth)/two-factor/page.tsx
 * @brief Completes a two-factor login. Reached only after /login responds
 *        with `requires_2fa: true`. The two_factor_token rides in the URL
 *        so a refresh on this page still recovers the flow.
 */
import { safeInternalLink } from "@/lib/safeLink";
import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Input, Button } from "@/components/ui";
import { AuthCard } from "@/components/auth/AuthCard";
import { verifyTwoFactorLogin } from "@/lib/api/auth";
import { completeLogin } from "@/lib/auth/flow";
import { formatApiError } from "@/lib/api/errors";

const Schema = z.object({
  code: z
    .string()
    .min(6, "Enter the 6-digit code")
    .max(8, "Codes are 6–8 characters"),
});
type FormData = z.infer<typeof Schema>;

export default function TwoFactorPage() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");
  const next = safeInternalLink(params.get("next")) ?? "/app";
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    mode: "onTouched",
    defaultValues: { code: "" },
  });

  if (!token) {
    return (
      <AuthCard
        title="Two-factor session expired"
        subtitle="Start the sign-in flow again to receive a fresh prompt."
      >
        <Link href="/login" className="underline">
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

  return (
    <AuthCard
      title="Two-factor verification"
      subtitle="Enter the 6-digit code from your authenticator app, or a backup code."
    >
      {error && (
        <p
          role="alert"
          className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error}
        </p>
      )}
      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="flex flex-col gap-4"
      >
        <Input
          label="Code"
          autoFocus
          autoComplete="one-time-code"
          inputMode="numeric"
          error={formState.errors.code?.message}
          disabled={formState.isSubmitting}
          {...register("code")}
        />
        <Button type="submit" size="lg" loading={formState.isSubmitting}>
          Verify
        </Button>
      </form>
    </AuthCard>
  );
}
