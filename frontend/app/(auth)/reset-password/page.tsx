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
import { useMutationWithToast } from "@/hooks/useMutationWithToast";

const RequestSchema = z.object({
  email: z.string().email("Enter a valid email address"),
});
const ConfirmSchema = z.object({
  new_password: z.string().min(12, "At least 12 characters"),
});
type RequestData = z.infer<typeof RequestSchema>;
type ConfirmData = z.infer<typeof ConfirmSchema>;

function RequestForm() {
  const [sent, setSent] = useState(false);
  const { register, handleSubmit, formState } = useForm<RequestData>({
    resolver: zodResolver(RequestSchema),
    mode: "onTouched",
    defaultValues: { email: "" },
  });

  const request = useMutationWithToast({
    mutationFn: (data: RequestData) => requestPasswordReset(data.email),
    successKey: "toasts.auth.reset.sent",
    errorKey: "toasts.auth.reset.failed",
    onSuccess: () => setSent(true),
  });
  const onSubmit = (data: RequestData) => request.mutate(data);

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
          disabled={request.isPending}
          {...register("email")}
        />
        <Button type="submit" size="lg" loading={request.isPending}>
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
  const [done, setDone] = useState(false);
  const { register, handleSubmit, formState } = useForm<ConfirmData>({
    resolver: zodResolver(ConfirmSchema),
    mode: "onTouched",
    defaultValues: { new_password: "" },
  });

  const confirm = useMutationWithToast({
    mutationFn: (data: ConfirmData) =>
      confirmPasswordReset(token, data.new_password),
    successKey: "toasts.auth.reset.done",
    errorKey: "toasts.auth.reset.confirmFailed",
    onSuccess: () => {
      setDone(true);
      setTimeout(() => router.replace("/login"), 1200);
    },
  });
  const onSubmit = (data: ConfirmData) => confirm.mutate(data);

  if (done) {
    return (
      <AuthCard title="Password updated" subtitle="Redirecting you to sign in…">
        <span />
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password">
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
          disabled={confirm.isPending}
          {...register("new_password")}
        />
        <Button type="submit" size="lg" loading={confirm.isPending}>
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
