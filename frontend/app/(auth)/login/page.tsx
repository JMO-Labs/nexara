"use client";
/**
 * @file app/(auth)/login/page.tsx
 * @brief Email/password login. Routes through 2FA when required, otherwise
 *        lands on /app (or the `next` query param).
 */
import { safeInternalLink } from "@/lib/safeLink";
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
import { useMutationWithToast } from "@/hooks/useMutationWithToast";

const Schema = z.object({
  email: z.string().min(3),
  password: z.string().min(1),
});
type FormData = z.infer<typeof Schema>;

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeInternalLink(params.get("next")) ?? "/app";

  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: { email: "", password: "" },
  });

  const login = useMutationWithToast({
    mutationFn: async (data: FormData) =>
      completeLogin(await apiLogin(data.email, data.password)),
    errorKey: "toasts.auth.login.failed",
    onSuccess: (out) => {
      if (out.kind === "two_factor") {
        const url = `/two-factor?token=${encodeURIComponent(out.two_factor_token)}&next=${encodeURIComponent(next)}`;
        router.push(url);
      } else {
        router.push(next);
      }
    },
  });
  const onSubmit = (data: FormData) => login.mutate(data);

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
        <Button type="submit" size="lg" loading={login.isPending}>
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
