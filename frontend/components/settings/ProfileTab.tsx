"use client";
/**
 * @file components/settings/ProfileTab.tsx
 * @brief Profile settings tab: display name, bio, location, website, title.
 */
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { SettingsRow, Input, Textarea, Button, Switch } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { useMyProfile, useUpdateProfile } from "@/hooks/useSettings";
import { ProfileDetailsPanel } from "./ProfileDetailsPanel";
import { HouseholdPanel } from "./HouseholdPanel";
import { VisibilitySelect } from "./VisibilitySelect";
import { AvatarPicker } from "./AvatarPicker";
import { TimezoneSelect } from "./TimezoneSelect";
import { GravatarEmailInput } from "./GravatarEmailInput";

const GRAVATAR = "https://www.gravatar.com/avatar/";

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

  // Sync server data into the form, but never clobber fields the user has
  // already edited (profile can load or refetch after they start typing).
  useEffect(() => {
    if (profile) reset(toFormData(profile), { keepDirtyValues: true });
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
    <div className="flex flex-col gap-5">
      <Panel title="Profile information">
        <SettingsRow
          label="Profile photo"
          description="Shown next to your name everywhere. Without one, your initials show on a color."
        >
          <AvatarPicker
            name={profile?.display_name ?? ""}
            src={profile?.avatar_url}
            disabled={isPending}
            onChange={(id) => mutate({ avatar_media_id: id })}
          />
        </SettingsRow>
        <SettingsRow
          label="Use my Gravatar"
          description="Show the photo linked to your email on gravatar.com when you haven't uploaded one. This shares a hash of your email with Gravatar."
        >
          <Switch
            aria-label="Use my Gravatar"
            checked={!!profile?.avatar_url?.startsWith(GRAVATAR)}
            onCheckedChange={(v) => mutate({ use_gravatar: v })}
            disabled={
              isPending ||
              (!!profile?.avatar_url &&
                !profile.avatar_url.startsWith(GRAVATAR))
            }
          />
          <GravatarEmailInput
            loginEmail={profile?.email}
            disabled={
              !!profile?.avatar_url && !profile.avatar_url.startsWith(GRAVATAR)
            }
          />
        </SettingsRow>
        <TimezoneSelect />
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <SettingsRow
            label="Display name"
            description="How you appear to other members."
          >
            <Input
              type="text"
              aria-label="Display name"
              error={err.display_name?.message}
              {...register("display_name")}
            />
          </SettingsRow>

          <SettingsRow label="Bio" description="Tell us about yourself.">
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <Textarea
                  aria-label="Bio"
                  rows={3}
                  placeholder="What's your story?"
                  error={err.bio?.message}
                  {...register("bio")}
                />
              </div>
              <VisibilitySelect field="bio" label="bio" />
            </div>
          </SettingsRow>

          <SettingsRow label="Location" description="Your location (optional).">
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <Input
                  type="text"
                  aria-label="Location"
                  placeholder="City, State"
                  error={err.location?.message}
                  {...register("location")}
                />
              </div>
              <VisibilitySelect field="location" label="location" />
            </div>
          </SettingsRow>

          <SettingsRow label="Website" description="Link to your website.">
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <Input
                  type="url"
                  aria-label="Website"
                  placeholder="https://example.com"
                  error={err.website_url?.message}
                  {...register("website_url")}
                />
              </div>
              <VisibilitySelect field="website_url" label="website" />
            </div>
          </SettingsRow>

          <SettingsRow label="Title" description="Your professional title.">
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <Input
                  type="text"
                  aria-label="Title"
                  placeholder="e.g., Designer"
                  error={err.title?.message}
                  {...register("title")}
                />
              </div>
              <VisibilitySelect field="title" label="title" />
            </div>
          </SettingsRow>

          <SettingsRow
            label="Pronouns (optional)"
            description={`Shown next to your name. ${pronounsLen}/50`}
          >
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <Input
                  type="text"
                  aria-label="Pronouns (optional)"
                  placeholder="e.g., she/her, they/them"
                  maxLength={50}
                  error={err.pronouns?.message}
                  {...register("pronouns")}
                />
              </div>
              <VisibilitySelect field="pronouns" label="pronouns" />
            </div>
          </SettingsRow>

          <div className="mt-4">
            <Button type="submit" loading={isPending} disabled={isPending}>
              Save profile
            </Button>
          </div>
        </form>
      </Panel>
      <ProfileDetailsPanel />
      <HouseholdPanel />
    </div>
  );
}
