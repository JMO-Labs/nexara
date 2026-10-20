"use client";
/**
 * @file app/(auth)/login/page.tsx
 * @brief Email/password login. Routes through 2FA when required, otherwise
 *        lands on /app (or the `next` query param).
 */
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Input, Button } from "@/components/ui";
import { AuthCard } from "@/components/auth/AuthCard";
import { OAuthButtons } from "@/components/auth/OAuthButtons";
import { login as apiLogin } from "@/lib/api/auth";
import { completeLogin } from "@/lib/auth/flow";
import { formatApiError } from "@/lib/api/errors";

const Schema = z.object({
  email: z.string().min(3),
  password: z.string().min(1),
});
type FormData = z.infer<typeof Schema>;

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") ?? "/app";
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (data: FormData) => {
    setError(null);
    try {
      const resp = await apiLogin(data.email, data.password);
      const out = await completeLogin(resp);
      if (out.kind === "two_factor") {
        const url = `/two-factor?token=${encodeURIComponent(out.two_factor_token)}&next=${encodeURIComponent(next)}`;
        router.push(url);
      } else {
        router.push(next);
      }
    } catch (e) {
      setError(formatApiError(e, "Sign-in failed."));
    }
  };

  return (
    <AuthCard
      title="Welcome back"
      subtitle={
        <>
          New here?{" "}
          <Link href="/register" className="underline">
            Create an account
          </Link>
        </>
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
        <Input
          label="Password"
          type="password"
          autoComplete="current-password"
          error={formState.errors.password?.message}
          {...register("password")}
        />
        <Button type="submit" size="lg" loading={formState.isSubmitting}>
          Sign in
        </Button>
        <div className="flex justify-between text-sm">
          <Link href="/magic-link" className="underline">
            Email a magic link
          </Link>
          <Link href="/reset-password" className="underline">
            Forgot password?
          </Link>
        </div>
      </form>
      <OAuthButtons />
    </AuthCard>
  );
}
