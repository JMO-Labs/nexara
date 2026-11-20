"use client";
/**
 * @file components/settings/PrivacyTab.tsx
 * @brief Privacy settings tab: visibility, presence, birthday, plugins. Explicit Save.
 */
import { useState } from "react";
import { Button, Option, Select, SettingsRow, Switch } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { useUpdateSettings, useUserSettings } from "@/hooks/useSettings";
import type { PrivacyAppearanceSettings } from "@/lib/api/settings";

type Draft = Partial<PrivacyAppearanceSettings>;

/**
 * @brief Privacy preferences form.
 * @return privacy tab content
 */
export function PrivacyTab() {
  const { data: settings } = useUserSettings();
  const { mutate, isPending } = useUpdateSettings();
  const [draft, setDraft] = useState<Draft>({});

  if (!settings) {
    return (
      <p role="status" className="text-sm text-muted">
        Loading privacy settings...
      </p>
    );
  }

  const value = { ...settings, ...draft };
  const dirty = Object.keys(draft).length > 0;
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) =>
    setDraft((d) => {
      const next = { ...d, [k]: v };
      if (settings[k] === v) delete next[k];
      return next;
    });

  const toggle = (k: keyof Draft, label: string, description?: string) => (
    <SettingsRow label={label} description={description}>
      <Switch
        aria-label={label}
        checked={value[k] as boolean}
        onCheckedChange={(v) => set(k, v as never)}
      />
    </SettingsRow>
  );

  const onSave = () => mutate(draft, { onSuccess: () => setDraft({}) });

  return (
    <div className="flex flex-col gap-4">
      <Panel title="Profile visibility">
        <SettingsRow
          label="Profile visible to"
          description="Who can open your profile."
        >
          <Select
            label="Profile visible to"
            value={value.profile_visible_to}
            onValueChange={(v) => set("profile_visible_to", v as never)}
          >
            <Option value="community">Community</Option>
            <Option value="admin_only">Admins only</Option>
          </Select>
        </SettingsRow>
      </Panel>

      <Panel title="Status and presence">
        {toggle("show_online_status", "Show online status")}
        {toggle("show_last_seen", "Show last seen")}
      </Panel>

      <Panel title="Birthday">
        <SettingsRow label="Show birthday to">
          <Select
            label="Show birthday to"
            value={value.show_birthday_to}
            onValueChange={(v) => set("show_birthday_to", v as never)}
          >
            <Option value="nobody">Nobody</Option>
            <Option value="community">Community</Option>
            <Option value="admin_only">Admins only</Option>
          </Select>
        </SettingsRow>
        {toggle("show_birthday_year", "Show birthday year")}
      </Panel>

      <Panel title="Plugin preferences">
        {toggle(
          "allow_sassybot",
          "Allow Sassybot",
          "Let Sassybot interact with you.",
        )}
        <div className="mt-4 flex justify-end">
          <Button onClick={onSave} disabled={!dirty || isPending}>
            Save
          </Button>
        </div>
      </Panel>
    </div>
  );
}
