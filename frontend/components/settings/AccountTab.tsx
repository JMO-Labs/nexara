'use client';
/**
 * @file components/settings/AccountTab.tsx
 * @brief Account settings tab: email change form with two-column layout.
 */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Stack from '@mui/joy/Stack';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import FormHelperText from '@mui/joy/FormHelperText';
import Typography from '@mui/joy/Typography';
import { Card, SettingsRow, Input, Button } from '@/components/ui';
import { useUpdateEmail } from '@/hooks/useSettings';

const Schema = z.object({
  email: z.string().email('Invalid email address'),
});
type FormData = z.infer<typeof Schema>;

export function AccountTab() {
  const [initialEmail] = useState('');
  const { mutate, isPending } = useUpdateEmail();
  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: { email: initialEmail },
  });

  const onSubmit = (data: FormData) => {
    mutate(data.email);
  };

  return (
    <Stack spacing={3} sx={{ maxWidth: 800 }}>
      <Card variant="outlined">
        <Typography level="title-md" component="h2" sx={{ mb: 2 }}>
          Email Address
        </Typography>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <SettingsRow
            label="Email"
            description="Your account email address used for login and recovery."
          >
            <Stack spacing={1} sx={{ width: '100%' }}>
              <FormControl error={!!formState.errors.email}>
                <FormLabel>Email Address</FormLabel>
                <Input
                  type="email"
                  placeholder="name@example.com"
                  slotProps={{
                    input: { autoComplete: 'email', ...register('email') },
                  }}
                />
              </FormControl>
              {formState.errors.email && (
                <FormHelperText>{formState.errors.email.message}</FormHelperText>
              )}
            </Stack>
          </SettingsRow>
          <Stack sx={{ mt: 2 }}>
            <Button
              type="submit"
              loading={isPending}
              disabled={isPending}
            >
              Update Email
            </Button>
          </Stack>
        </form>
      </Card>
    </Stack>
  );
}
