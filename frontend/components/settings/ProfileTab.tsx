"use client";
/**
 * @file components/settings/ProfileTab.tsx
 * @brief Profile settings tab: display name, bio, location, website, title.
 */
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, SettingsRow, Input, Textarea, Button } from "@/components/ui";
import { useUpdateProfile } from "@/hooks/useSettings";

const Schema = z.object({
  display_name: z.string().optional(),
  bio: z.string().optional(),
  location: z.string().optional(),
  website_url: z.string().url("Invalid URL").optional().or(z.literal("")),
  title: z.string().optional(),
});
type FormData = z.infer<typeof Schema>;

/**
 * @brief Profile edit form.
 * @return profile tab content
 */
export function ProfileTab() {
  const [initialValues] = useState<FormData>({});
  const { mutate, isPending } = useUpdateProfile();
  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: initialValues,
  });
  const err = formState.errors;

  const onSubmit = (data: FormData) => {
    const filtered: Record<string, unknown> = {};
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== "") {
        filtered[key] = value;
      }
    });
    mutate(filtered);
  };

  return (
    <Card className="max-w-3xl p-4 md:p-6">
      <h2 className="mb-2 text-lg font-semibold">Profile information</h2>
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <SettingsRow
          label="Display name"
          description="How you appear to other members."
        >
          <Input
            type="text"
            label="Display name"
            error={err.display_name?.message}
            {...register("display_name")}
          />
        </SettingsRow>

        <SettingsRow label="Bio" description="Tell us about yourself.">
          <Textarea
            label="Bio"
            rows={3}
            placeholder="What's your story?"
            error={err.bio?.message}
            {...register("bio")}
          />
        </SettingsRow>

        <SettingsRow label="Location" description="Your location (optional).">
          <Input
            type="text"
            label="Location"
            placeholder="City, State"
            error={err.location?.message}
            {...register("location")}
          />
        </SettingsRow>

        <SettingsRow label="Website" description="Link to your website.">
          <Input
            type="url"
            label="Website"
            placeholder="https://example.com"
            error={err.website_url?.message}
            {...register("website_url")}
          />
        </SettingsRow>

        <SettingsRow label="Title" description="Your professional title.">
          <Input
            type="text"
            label="Title"
            placeholder="e.g., Designer"
            error={err.title?.message}
            {...register("title")}
          />
        </SettingsRow>

        <div className="mt-4">
          <Button type="submit" loading={isPending} disabled={isPending}>
            Save profile
          </Button>
        </div>
      </form>
    </Card>
  );
}
