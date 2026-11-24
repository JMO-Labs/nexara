"use client";
/**
 * @file app/(auth)/login/page.tsx
 * @brief Email/password login. Routes through 2FA when required, otherwise
 *        lands on /app (or the `next` query param).
 */
import { safeInternalLink } from "@/lib/safeLink";
import { useEffect, useState } from "react";
import { useIsClient } from "@/hooks/useIsClient";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Input, Button } from "@/components/ui";
import { AuthCard } from "@/components/auth/AuthCard";
import { OAuthButtons } from "@/components/auth/OAuthButtons";
import { PasswordInput } from "@/components/auth/PasswordInput";
import {
  getAuthConfig,
  login as apiLogin,
  type OAuthProvider,
} from "@/lib/api/auth";
import { completeLogin, twoFactorUrl } from "@/lib/auth/flow";
import { authenticateWithPasskey, passkeysAvailable } from "@/lib/passkeys";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";

const Schema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof Schema>;

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeInternalLink(params.get("next")) ?? "/app";
  const isClient = useIsClient();
  const [providers, setProviders] = useState<OAuthProvider[]>([]);
  const [localAuth, setLocalAuth] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getAuthConfig()
      .then((cfg) => {
        if (cancelled) return;
        setProviders(cfg.oauth_providers);
        setLocalAuth(cfg.local_auth_enabled && !cfg.sso_only);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const { register, handleSubmit, formState, getValues } = useForm<FormData>({
    resolver: zodResolver(Schema),
    // Validate on submit only: leaving the email field for the passkey button
    // (email is an optional hint there) must not flag it as invalid.
    mode: "onSubmit",
    defaultValues: { email: "", password: "" },
  });

  const login = useMutationWithToast({
    mutationFn: async (data: FormData) =>
      completeLogin(await apiLogin(data.email, data.password)),
    errorKey: "toasts.auth.login.failed",
    onSuccess: (out) => {
      if (out.kind === "two_factor") {
        router.push(twoFactorUrl(next));
      } else {
        router.push(next);
      }
    },
  });
  const onSubmit = (data: FormData) => login.mutate(data);

  const passkey = useMutationWithToast({
    mutationFn: async () =>
      completeLogin(
        await authenticateWithPasskey({
          email: getValues("email") || undefined,
        }),
      ),
    errorKey: "toasts.auth.login.failed",
    onSuccess: (out) =>
      router.push(out.kind === "two_factor" ? twoFactorUrl(next) : next),
  });

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Sign in to catch up with your people."
      footer={
        <>
          New here?{" "}
          <Link
            href="/register"
            className="inline-flex min-h-11 items-center font-medium text-accent underline underline-offset-4"
          >
            Create an account
          </Link>
        </>
      }
    >
      {localAuth && (
        <form
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          className="flex flex-col gap-4"
        >
          <Input
            label="Email"
            type="email"
            autoFocus
            autoComplete="username webauthn"
            error={formState.errors.email?.message}
            disabled={login.isPending}
            {...register("email")}
          />
          <PasswordInput
            label="Password"
            autoComplete="current-password"
            error={formState.errors.password?.message}
            disabled={login.isPending}
            {...register("password")}
          />
          <div className="-my-2 flex justify-between text-sm">
            <Link
              href="/magic-link"
              className="inline-flex min-h-11 items-center text-muted underline-offset-4 hover:text-ink underline"
            >
              Email a magic link
            </Link>
            <Link
              href="/reset-password"
              className="inline-flex min-h-11 items-center text-muted underline-offset-4 hover:text-ink underline"
            >
              Forgot password?
            </Link>
          </div>
          <Button type="submit" size="lg" loading={login.isPending}>
            Sign in
          </Button>
          {isClient && passkeysAvailable() && (
            <Button
              type="button"
              size="lg"
              variant="ghost"
              loading={passkey.isPending}
              onClick={() => passkey.mutate(undefined)}
            >
              Sign in with a passkey
            </Button>
          )}
        </form>
      )}
      <OAuthButtons providers={providers} showDivider={localAuth} />
    </AuthCard>
  );
}
