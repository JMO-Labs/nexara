"use client";
/**
 * @file app/(auth)/magic-link/page.tsx
 * @brief Request a passwordless sign-in link via email. The verify step is
 *        handled at /magic-link/verify when the user clicks through.
 */
import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Stack from "@mui/joy/Stack";
import FormControl from "@mui/joy/FormControl";
import FormLabel from "@mui/joy/FormLabel";
import FormHelperText from "@mui/joy/FormHelperText";
import Alert from "@mui/joy/Alert";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { AuthCard } from "@/components/auth/AuthCard";
import { requestMagicLink } from "@/lib/api/auth";
import { formatApiError } from "@/lib/api/errors";

const Schema = z.object({ email: z.string().min(3) });
type FormData = z.infer<typeof Schema>;

export default function MagicLinkPage() {
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: { email: "" },
  });

  const onSubmit = async (data: FormData) => {
    setError(null);
    try {
      await requestMagicLink(data.email);
      setSent(true);
    } catch (e) {
      setError(formatApiError(e, "Could not send link."));
    }
  };

  if (sent) {
    return (
      <AuthCard
        title="Check your inbox"
        subtitle="If an account exists for that email, a sign-in link is on its way. The link expires in 15 minutes."
      >
        <Link href="/login" style={{ textDecoration: "underline" }}>
          Back to sign-in
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Sign in with a magic link"
      subtitle="We'll email you a one-time link — no password needed."
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
          <Button
            type="submit"
            size="lg"
            loading={formState.isSubmitting}
            fullWidth
          >
            Email me a link
          </Button>
          <Link href="/login" style={{ textDecoration: "underline" }}>
            Back to sign-in
          </Link>
        </Stack>
      </form>
    </AuthCard>
  );
}
