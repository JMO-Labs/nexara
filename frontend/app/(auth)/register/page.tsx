"use client";
/**
 * @file app/(auth)/register/page.tsx
 * @brief Local-account registration. Honours `?invite=` for closed instances.
 */
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Input, Button } from "@/components/ui";
import { AuthCard } from "@/components/auth/AuthCard";
import { register as apiRegister } from "@/lib/api/auth";
import { completeLogin } from "@/lib/auth/flow";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";

const Schema = z.object({
  display_name: z.string().min(1, "Required").max(100),
  username: z
    .string()
    .min(3)
    .max(30)
    .regex(/^[a-zA-Z0-9_-]+$/, "Letters, numbers, _ or - only"),
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(12, "At least 12 characters"),
});
type FormData = z.infer<typeof Schema>;

export default function RegisterPage() {
  const router = useRouter();
  const params = useSearchParams();
  const invite = params.get("invite") ?? undefined;

  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    mode: "onTouched",
    defaultValues: { display_name: "", username: "", email: "", password: "" },
  });

  const signUp = useMutationWithToast({
    mutationFn: async (data: FormData) =>
      completeLogin(await apiRegister({ ...data, invite_token: invite })),
    errorKey: "toasts.auth.register.failed",
    onSuccess: () => router.push("/app"),
  });
  const onSubmit = (data: FormData) => signUp.mutate(data);

  return (
    <AuthCard
      title="Create your account"
      subtitle={
        <>
          Already a member?{" "}
          <Link href="/login" className="underline">
            Sign in
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
          label="Display name"
          autoFocus
          error={formState.errors.display_name?.message}
          disabled={signUp.isPending}
          {...register("display_name")}
        />
        <Input
          label="Username"
          autoComplete="username"
          error={formState.errors.username?.message}
          disabled={signUp.isPending}
          {...register("username")}
        />
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          error={formState.errors.email?.message}
          disabled={signUp.isPending}
          {...register("email")}
        />
        <Input
          label="Password"
          type="password"
          autoComplete="new-password"
          hint="At least 12 characters."
          error={formState.errors.password?.message}
          disabled={signUp.isPending}
          {...register("password")}
        />
        <Button type="submit" size="lg" loading={signUp.isPending}>
          Create account
        </Button>
      </form>
    </AuthCard>
  );
}
