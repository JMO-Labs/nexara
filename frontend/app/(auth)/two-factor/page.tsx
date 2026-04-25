'use client';
/**
 * @file app/(auth)/two-factor/page.tsx
 * @brief Completes a two-factor login. Reached only after /login responds
 *        with `requires_2fa: true`. The two_factor_token rides in the URL
 *        so a refresh on this page still recovers the flow.
 */
import { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Stack from '@mui/joy/Stack';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import FormHelperText from '@mui/joy/FormHelperText';
import Alert from '@mui/joy/Alert';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { AuthCard } from '@/components/auth/AuthCard';
import { verifyTwoFactorLogin } from '@/lib/api/auth';
import { completeLogin } from '@/lib/auth/flow';
import { formatApiError } from '@/lib/api/errors';

const Schema = z.object({
  code: z
    .string()
    .min(6, 'Enter the 6-digit code')
    .max(8, 'Codes are 6–8 characters'),
});
type FormData = z.infer<typeof Schema>;

export default function TwoFactorPage() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get('token');
  const next = params.get('next') ?? '/app';
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: { code: '' },
  });

  if (!token) {
    return (
      <AuthCard
        title="Two-factor session expired"
        subtitle="Start the sign-in flow again to receive a fresh prompt."
      >
        <Link href="/login" style={{ textDecoration: 'underline' }}>
          Back to sign-in
        </Link>
      </AuthCard>
    );
  }

  const onSubmit = async (data: FormData) => {
    setError(null);
    try {
      const resp = await verifyTwoFactorLogin(token, data.code.trim());
      await completeLogin(resp);
      router.replace(next);
    } catch (e) {
      setError(formatApiError(e, 'Code rejected.'));
    }
  };

  return (
    <AuthCard
      title="Two-factor verification"
      subtitle="Enter the 6-digit code from your authenticator app, or a backup code."
    >
      {error && (
        <Alert color="danger" variant="soft">
          {error}
        </Alert>
      )}
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <Stack spacing={2.5}>
          <FormControl error={!!formState.errors.code}>
            <FormLabel>Code</FormLabel>
            <Input
              autoFocus
              slotProps={{
                input: {
                  autoComplete: 'one-time-code',
                  inputMode: 'numeric',
                  ...register('code'),
                },
              }}
            />
            {formState.errors.code && (
              <FormHelperText>{formState.errors.code.message}</FormHelperText>
            )}
          </FormControl>
          <Button type="submit" size="lg" loading={formState.isSubmitting} fullWidth>
            Verify
          </Button>
        </Stack>
      </form>
    </AuthCard>
  );
}
