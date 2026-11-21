"use client";
/**
 * @file components/settings/NudgePreferences.tsx
 * @brief Engagement settings: opt in/out of nudges and gentle reminders.
 */
import { SettingsRow, Skeleton, Switch } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { useUpdateSettings, useUserSettings } from "@/hooks/useSettings";

/**
 * @brief Nudge preference toggles (default on), saved via PUT /settings.
 * @return engagement settings card
 */
export function NudgePreferences() {
  const { data, isLoading } = useUserSettings();
  const { mutate } = useUpdateSettings();

  if (isLoading) return <Skeleton height={160} rounded="lg" />;

  return (
    <Panel title="Engagement">
      <SettingsRow
        label="Receive nudges"
        description="Let others nudge you as a friendly reminder"
      >
        <Switch
          aria-label="Receive nudges"
          checked={data?.receive_nudges ?? true}
          onCheckedChange={(v) => mutate({ receive_nudges: v })}
        />
      </SettingsRow>
      <SettingsRow
        label="Receive gentle reminders"
        description="Let us send you gentle reminders if you're inactive for 2 weeks"
      >
        <Switch
          aria-label="Receive gentle reminders"
          checked={data?.receive_gentle_nudges ?? true}
          onCheckedChange={(v) => mutate({ receive_gentle_nudges: v })}
        />
      </SettingsRow>
    </Panel>
  );
}
