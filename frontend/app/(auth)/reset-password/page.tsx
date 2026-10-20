"use client";
/**
 * @file app/(auth)/reset-password/page.tsx
 * @brief Two modes: request a reset email (no `?token=`), or set a new
 *        password (with `?token=`). Single page keeps deep links simple.
 */
import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Input, Button } from "@/components/ui";
import { AuthCard } from "@/components/auth/AuthCard";
import { requestPasswordReset, confirmPasswordReset } from "@/lib/api/auth";
import { formatApiError } from "@/lib/api/errors";

const RequestSchema = z.object({ email: z.string().min(3) });
const ConfirmSchema = z.object({
  new_password: z.string().min(12, "At least 12 characters"),
});
type RequestData = z.infer<typeof RequestSchema>;
type ConfirmData = z.infer<typeof ConfirmSchema>;

function RequestForm() {
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<RequestData>({
    resolver: zodResolver(RequestSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = async (data: RequestData) => {
    setError(null);
    try {
      await requestPasswordReset(data.email);
      setSent(true);
    } catch (e) {
      setError(formatApiError(e, "Could not send reset email."));
    }
  };

  if (sent) {
    return (
      <AuthCard
        title="Check your inbox"
        subtitle="If an account exists, we've sent a password-reset link."
      >
        <Link href="/login" className="underline">
          Back to sign-in
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Reset your password"
      subtitle="Enter your email and we'll send a reset link."
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
          label="Email"
          type="email"
          autoFocus
          autoComplete="email"
          error={formState.errors.email?.message}
          {...register("email")}
        />
        <Button type="submit" size="lg" loading={formState.isSubmitting}>
          Email reset link
        </Button>
        <Link href="/login" className="underline">
          Back to sign-in
        </Link>
      </form>
    </AuthCard>
  );
}

function ConfirmForm({ token }: { token: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const { register, handleSubmit, formState } = useForm<ConfirmData>({
    resolver: zodResolver(ConfirmSchema),
    defaultValues: { new_password: "" },
  });

  const onSubmit = async (data: ConfirmData) => {
    setError(null);
    try {
      await confirmPasswordReset(token, data.new_password);
      setDone(true);
      setTimeout(() => router.replace("/login"), 1200);
    } catch (e) {
      setError(formatApiError(e, "Reset failed."));
    }
  };

  if (done) {
    return (
      <AuthCard title="Password updated" subtitle="Redirecting you to sign in…">
        <span />
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password">
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
          label="New password"
          type="password"
          autoFocus
          autoComplete="new-password"
          hint="At least 12 characters."
          error={formState.errors.new_password?.message}
          {...register("new_password")}
        />
        <Button type="submit" size="lg" loading={formState.isSubmitting}>
          Update password
        </Button>
      </form>
    </AuthCard>
  );
}

export default function ResetPasswordPage() {
  const params = useSearchParams();
  const token = params.get("token");
  return token ? <ConfirmForm token={token} /> : <RequestForm />;
}
