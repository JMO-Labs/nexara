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
import Stack from "@mui/joy/Stack";
import FormControl from "@mui/joy/FormControl";
import FormLabel from "@mui/joy/FormLabel";
import FormHelperText from "@mui/joy/FormHelperText";
import Typography from "@mui/joy/Typography";
import Alert from "@mui/joy/Alert";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
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
          <Link href="/register" style={{ textDecoration: "underline" }}>
            Create an account
          </Link>
        </>
      }
    >
      {error && (
        <Alert color="danger" variant="soft">
          {error}
        </Alert>
      )}
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <Stack spacing={2.5}>
          <FormControl error={!!formState.errors.email}>
            <FormLabel>Email</FormLabel>
            <Input
              type="email"
              autoFocus
              slotProps={{
                input: { autoComplete: "email", ...register("email") },
              }}
            />
            {formState.errors.email && (
              <FormHelperText>{formState.errors.email.message}</FormHelperText>
            )}
          </FormControl>
          <FormControl error={!!formState.errors.password}>
            <FormLabel>Password</FormLabel>
            <Input
              type="password"
              slotProps={{
                input: {
                  autoComplete: "current-password",
                  ...register("password"),
                },
              }}
            />
            {formState.errors.password && (
              <FormHelperText>
                {formState.errors.password.message}
              </FormHelperText>
            )}
          </FormControl>
          <Button
            type="submit"
            size="lg"
            loading={formState.isSubmitting}
            fullWidth
          >
            Sign in
          </Button>
          <Stack direction="row" justifyContent="space-between">
            <Typography level="body-sm">
              <Link href="/magic-link">Email a magic link</Link>
            </Typography>
            <Typography level="body-sm">
              <Link href="/reset-password">Forgot password?</Link>
            </Typography>
          </Stack>
        </Stack>
      </form>
      <OAuthButtons />
    </AuthCard>
  );
}
