'use client';
/**
 * @file components/settings/AccountTab.tsx
 * @brief Account settings tab: email change form.
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
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useUpdateEmail } from '@/hooks/useSettings';

const Schema = z.object({
  email: z.string().email('Invalid email address'),
});
type FormData = z.infer<typeof Schema>;

export function AccountTab() {
  const [initialEmail] = useState(''); // Placeholder; normally from useMe()
  const { mutate, isPending } = useUpdateEmail();
  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: { email: initialEmail },
  });

  const onSubmit = (data: FormData) => {
    mutate(data.email);
  };

  return (
    <Stack spacing={3}>
      <div>
        <Typography level="h3">Email Address</Typography>
        <Typography level="body-sm" color="neutral">
          Update your account email address.
        </Typography>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <Stack spacing={2}>
          <FormControl error={!!formState.errors.email}>
            <FormLabel>Email Address</FormLabel>
            <Input
              type="email"
              slotProps={{
                input: { autoComplete: 'email', ...register('email') },
              }}
            />
            {formState.errors.email && (
              <FormHelperText>{formState.errors.email.message}</FormHelperText>
            )}
          </FormControl>
          <div>
            <Button
              type="submit"
              loading={isPending}
              disabled={isPending}
            >
              Update Email
            </Button>
          </div>
        </Stack>
      </form>
    </Stack>
  );
}
