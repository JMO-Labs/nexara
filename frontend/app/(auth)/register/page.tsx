"use client";
/**
 * @file app/(auth)/register/page.tsx
 * @brief Local-account registration. Honours `?invite=` for closed instances.
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
import Alert from "@mui/joy/Alert";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { AuthCard } from "@/components/auth/AuthCard";
import { register as apiRegister } from "@/lib/api/auth";
import { completeLogin } from "@/lib/auth/flow";
import { formatApiError } from "@/lib/api/errors";

const Schema = z.object({
  display_name: z.string().min(1, "Required").max(100),
  username: z
    .string()
    .min(3)
    .max(30)
    .regex(/^[a-zA-Z0-9_-]+$/, "Letters, numbers, _ or - only"),
  email: z.string().min(3),
  password: z.string().min(12, "At least 12 characters"),
});
type FormData = z.infer<typeof Schema>;

export default function RegisterPage() {
  const router = useRouter();
  const params = useSearchParams();
  const invite = params.get("invite") ?? undefined;
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: { display_name: "", username: "", email: "", password: "" },
  });

  const onSubmit = async (data: FormData) => {
    setError(null);
    try {
      const resp = await apiRegister({ ...data, invite_token: invite });
      await completeLogin(resp);
      router.push("/app");
    } catch (e) {
      setError(formatApiError(e, "Registration failed."));
    }
  };

  return (
    <AuthCard
      title="Create your account"
      subtitle={
        <>
          Already a member?{" "}
          <Link href="/login" style={{ textDecoration: "underline" }}>
            Sign in
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
          <FormControl error={!!formState.errors.display_name}>
            <FormLabel>Display name</FormLabel>
            <Input
              autoFocus
              slotProps={{ input: { ...register("display_name") } }}
            />
            {formState.errors.display_name && (
              <FormHelperText>
                {formState.errors.display_name.message}
              </FormHelperText>
            )}
          </FormControl>
          <FormControl error={!!formState.errors.username}>
            <FormLabel>Username</FormLabel>
            <Input
              slotProps={{
                input: { autoComplete: "username", ...register("username") },
              }}
            />
            {formState.errors.username && (
              <FormHelperText>
                {formState.errors.username.message}
              </FormHelperText>
            )}
          </FormControl>
          <FormControl error={!!formState.errors.email}>
            <FormLabel>Email</FormLabel>
            <Input
              type="email"
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
                  autoComplete: "new-password",
                  ...register("password"),
                },
              }}
            />
            <FormHelperText>
              {formState.errors.password?.message ?? "At least 12 characters."}
            </FormHelperText>
          </FormControl>
          <Button
            type="submit"
            size="lg"
            loading={formState.isSubmitting}
            fullWidth
          >
            Create account
          </Button>
        </Stack>
      </form>
    </AuthCard>
  );
}
