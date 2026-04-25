'use client';
/**
 * @file components/settings/ProfileTab.tsx
 * @brief Profile settings tab: display name, bio, location, website, title.
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
import { Textarea } from '@/components/ui/Textarea';
import { Button } from '@/components/ui/Button';
import { useUpdateProfile } from '@/hooks/useSettings';

const Schema = z.object({
  display_name: z.string().optional(),
  bio: z.string().optional(),
  location: z.string().optional(),
  website_url: z.string().url('Invalid URL').optional().or(z.literal('')),
  title: z.string().optional(),
});
type FormData = z.infer<typeof Schema>;

export function ProfileTab() {
  const [initialValues] = useState<FormData>({});
  const { mutate, isPending } = useUpdateProfile();
  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: initialValues,
  });

  const onSubmit = (data: FormData) => {
    const filtered: Record<string, unknown> = {};
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        filtered[key] = value;
      }
    });
    mutate(filtered);
  };

  return (
    <Stack spacing={3}>
      <div>
        <Typography level="h3">Profile Information</Typography>
        <Typography level="body-sm" color="neutral">
          Update your public profile information.
        </Typography>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <Stack spacing={2}>
          <FormControl error={!!formState.errors.display_name}>
            <FormLabel>Display Name</FormLabel>
            <Input
              type="text"
              slotProps={{
                input: { ...register('display_name') },
              }}
            />
            {formState.errors.display_name && (
              <FormHelperText>{formState.errors.display_name.message}</FormHelperText>
            )}
          </FormControl>

          <FormControl error={!!formState.errors.bio}>
            <FormLabel>Bio</FormLabel>
            <Textarea
              minRows={3}
              slotProps={{
                textarea: { ...register('bio') },
              }}
            />
            {formState.errors.bio && (
              <FormHelperText>{formState.errors.bio.message}</FormHelperText>
            )}
          </FormControl>

          <FormControl error={!!formState.errors.location}>
            <FormLabel>Location</FormLabel>
            <Input
              type="text"
              slotProps={{
                input: { ...register('location') },
              }}
            />
            {formState.errors.location && (
              <FormHelperText>{formState.errors.location.message}</FormHelperText>
            )}
          </FormControl>

          <FormControl error={!!formState.errors.website_url}>
            <FormLabel>Website</FormLabel>
            <Input
              type="url"
              placeholder="https://example.com"
              slotProps={{
                input: { ...register('website_url') },
              }}
            />
            {formState.errors.website_url && (
              <FormHelperText>{formState.errors.website_url.message}</FormHelperText>
            )}
          </FormControl>

          <FormControl error={!!formState.errors.title}>
            <FormLabel>Title</FormLabel>
            <Input
              type="text"
              slotProps={{
                input: { ...register('title') },
              }}
            />
            {formState.errors.title && (
              <FormHelperText>{formState.errors.title.message}</FormHelperText>
            )}
          </FormControl>

          <div>
            <Button
              type="submit"
              loading={isPending}
              disabled={isPending}
            >
              Save Profile
            </Button>
          </div>
        </Stack>
      </form>
    </Stack>
  );
}
