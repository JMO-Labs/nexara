"use client";
/**
 * @file components/settings/ProfileTab.tsx
 * @brief Profile settings tab: display name, bio, location, website, title.
 */
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { SettingsRow, Input, Textarea, Button } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { useMyProfile, useUpdateProfile } from "@/hooks/useSettings";

const Schema = z.object({
  display_name: z.string().optional(),
  bio: z.string().optional(),
  location: z.string().optional(),
  website_url: z.string().url("Invalid URL").optional().or(z.literal("")),
  title: z.string().optional(),
  pronouns: z.string().max(50, "Max 50 characters").optional(),
});
type FormData = z.infer<typeof Schema>;

const FIELDS = [
  "display_name",
  "bio",
  "location",
  "website_url",
  "title",
  "pronouns",
] as const;

/** @brief Map a profile to form values (null -> empty string). */
function toFormData(
  p: Partial<Record<(typeof FIELDS)[number], string | null>>,
) {
  const out: FormData = {};
  FIELDS.forEach((k) => {
    out[k] = p[k] ?? "";
  });
  return out;
}

/**
 * @brief Profile edit form.
 * @return profile tab content
 */
export function ProfileTab() {
  const { data: profile } = useMyProfile();
  const { mutate, isPending } = useUpdateProfile();
  const { register, handleSubmit, formState, watch, reset } = useForm<FormData>(
    { resolver: zodResolver(Schema), defaultValues: {} },
  );
  const err = formState.errors;
  const pronounsLen = (watch("pronouns") ?? "").length;

  useEffect(() => {
    if (profile) reset(toFormData(profile));
  }, [profile, reset]);

  const onSubmit = (data: FormData) => {
    const base = profile ? toFormData(profile) : ({} as FormData);
    const changed: Record<string, string> = {};
    (Object.keys(data) as (keyof FormData)[]).forEach((key) => {
      const next = data[key] ?? "";
      if (next !== (base[key] ?? "")) changed[key] = next;
    });
    if (Object.keys(changed).length > 0) mutate(changed);
  };

  return (
    <Panel title="Profile information">
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

        <SettingsRow
          label="Pronouns (optional)"
          description={`Shown next to your name. ${pronounsLen}/50`}
        >
          <Input
            type="text"
            label="Pronouns (optional)"
            placeholder="e.g., she/her, they/them"
            maxLength={50}
            error={err.pronouns?.message}
            {...register("pronouns")}
          />
        </SettingsRow>

        <div className="mt-4">
          <Button type="submit" loading={isPending} disabled={isPending}>
            Save profile
          </Button>
        </div>
      </form>
    </Panel>
  );
}
