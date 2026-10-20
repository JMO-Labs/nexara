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
import { Input, Button } from "@/components/ui";
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
        <Link href="/login" className="underline">
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
          Email me a link
        </Button>
        <Link href="/login" className="underline">
          Back to sign-in
        </Link>
      </form>
    </AuthCard>
  );
}
