'use client';
/**
 * @file components/settings/ProfileTab.tsx
 * @brief Profile settings tab with two-column layout: display name, bio, location, website, title.
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
import { Card, SettingsRow, Input, Textarea, Button } from '@/components/ui';
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
    <Stack spacing={3} sx={{ maxWidth: 800 }}>
      <Card variant="outlined">
        <Typography level="title-md" component="h2" sx={{ mb: 2 }}>
          Profile Information
        </Typography>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <SettingsRow label="Display Name" description="How you appear to other members.">
            <Stack spacing={1} sx={{ width: '100%' }}>
              <FormControl error={!!formState.errors.display_name}>
                <FormLabel>Display Name</FormLabel>
                <Input
                  type="text"
                  slotProps={{
                    input: { ...register('display_name') },
                  }}
                />
              </FormControl>
              {formState.errors.display_name && (
                <FormHelperText>{formState.errors.display_name.message}</FormHelperText>
              )}
            </Stack>
          </SettingsRow>

          <SettingsRow label="Bio" description="Tell us about yourself.">
            <Stack spacing={1} sx={{ width: '100%' }}>
              <FormControl error={!!formState.errors.bio}>
                <FormLabel>Bio</FormLabel>
                <Textarea
                  minRows={3}
                  placeholder="What's your story?"
                  slotProps={{
                    textarea: { ...register('bio') },
                  }}
                />
              </FormControl>
              {formState.errors.bio && (
                <FormHelperText>{formState.errors.bio.message}</FormHelperText>
              )}
            </Stack>
          </SettingsRow>

          <SettingsRow label="Location" description="Your location (optional).">
            <Stack spacing={1} sx={{ width: '100%' }}>
              <FormControl error={!!formState.errors.location}>
                <FormLabel>Location</FormLabel>
                <Input
                  type="text"
                  placeholder="City, State"
                  slotProps={{
                    input: { ...register('location') },
                  }}
                />
              </FormControl>
              {formState.errors.location && (
                <FormHelperText>{formState.errors.location.message}</FormHelperText>
              )}
            </Stack>
          </SettingsRow>

          <SettingsRow label="Website" description="Link to your website.">
            <Stack spacing={1} sx={{ width: '100%' }}>
              <FormControl error={!!formState.errors.website_url}>
                <FormLabel>Website</FormLabel>
                <Input
                  type="url"
                  placeholder="https://example.com"
                  slotProps={{
                    input: { ...register('website_url') },
                  }}
                />
              </FormControl>
              {formState.errors.website_url && (
                <FormHelperText>{formState.errors.website_url.message}</FormHelperText>
              )}
            </Stack>
          </SettingsRow>

          <SettingsRow label="Title" description="Your professional title.">
            <Stack spacing={1} sx={{ width: '100%' }}>
              <FormControl error={!!formState.errors.title}>
                <FormLabel>Title</FormLabel>
                <Input
                  type="text"
                  placeholder="e.g., Designer"
                  slotProps={{
                    input: { ...register('title') },
                  }}
                />
              </FormControl>
              {formState.errors.title && (
                <FormHelperText>{formState.errors.title.message}</FormHelperText>
              )}
            </Stack>
          </SettingsRow>

          <Stack sx={{ mt: 2 }}>
            <Button
              type="submit"
              loading={isPending}
              disabled={isPending}
            >
              Save Profile
            </Button>
          </Stack>
        </form>
      </Card>
    </Stack>
  );
}
