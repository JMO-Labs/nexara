"use client";
/**
 * @file components/settings/AppearanceTab.tsx
 * @brief Appearance settings tab: theme (radio group) and language.
 */
import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Card, SettingsRow, Select, Option, Switch } from "@/components/ui";
import { RadioGroup, RadioGroupItem } from "@/components/ui/shadcn/radio-group";
import { cn } from "@/lib/utils";
import type { UserSettings } from "@/lib/api/settings";
import { useUpdateSettings, useUserSettings } from "@/hooks/useSettings";

type FontSize = UserSettings["font_size"];

const THEMES = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
] as const;

const FONT_SIZES = [
  { value: "small", label: "Small", cls: "text-xs" },
  { value: "medium", label: "Medium", cls: "text-sm" },
  { value: "large", label: "Large", cls: "text-base" },
] as const;

/**
 * @brief Theme, font size, compact feed and language preferences.
 * @return appearance tab content
 */
export function AppearanceTab() {
  const { theme, setTheme } = useTheme();
  const { data: settings } = useUserSettings();
  const { mutate, isPending } = useUpdateSettings();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // next-themes SSR-safe mount detection — setState in effect is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  if (!mounted || !settings) {
    return (
      <p role="status" className="text-sm text-muted">
        Loading appearance settings...
      </p>
    );
  }

  const sizeClass =
    FONT_SIZES.find((f) => f.value === settings.font_size)?.cls ?? "text-sm";

  const onTheme = (value: string) => {
    setTheme(value);
    mutate({ theme: value as "system" | "light" | "dark" });
  };

  return (
    <Card className="max-w-3xl p-4 md:p-6">
      <h2 className="mb-2 text-lg font-semibold">Appearance</h2>

      <SettingsRow
        label="Theme"
        description="Choose light, dark, or follow your device."
      >
        <RadioGroup
          aria-label="Theme"
          value={theme || "system"}
          onValueChange={onTheme}
          disabled={isPending}
        >
          {THEMES.map(({ value, label }) => (
            <label
              key={value}
              htmlFor={`theme-${value}`}
              className="flex min-h-11 items-center gap-3 text-sm"
            >
              <RadioGroupItem id={`theme-${value}`} value={value} />
              {label}
            </label>
          ))}
        </RadioGroup>
      </SettingsRow>

      <SettingsRow label="Font size" description="Text size in the app.">
        <RadioGroup
          aria-label="Font size"
          value={settings.font_size}
          onValueChange={(v) => mutate({ font_size: v as FontSize })}
          disabled={isPending}
        >
          {FONT_SIZES.map(({ value, label }) => (
            <label
              key={value}
              htmlFor={`font-${value}`}
              className="flex min-h-11 items-center gap-3 text-sm"
            >
              <RadioGroupItem id={`font-${value}`} value={value} />
              {label}
            </label>
          ))}
        </RadioGroup>
      </SettingsRow>

      <SettingsRow
        label="Compact feed"
        description="Tighter spacing between feed items."
      >
        <Switch
          aria-label="Compact feed"
          checked={settings.compact_feed}
          onCheckedChange={(v) => mutate({ compact_feed: v })}
          disabled={isPending}
        />
      </SettingsRow>

      <SettingsRow label="Preview" description="How your choices look.">
        <div
          data-testid="appearance-preview"
          data-font-size={settings.font_size}
          aria-live="polite"
          className={cn(
            "rounded-xl border border-ink/10 bg-surface p-3",
            sizeClass,
            settings.compact_feed ? "space-y-1" : "space-y-3",
          )}
        >
          <p className="font-semibold">Sample post title</p>
          <p>Text sizing and spacing update as you change settings.</p>
          <p className="text-muted">Posted just now</p>
        </div>
      </SettingsRow>

      <SettingsRow
        label="Language"
        description="Select your preferred language."
      >
        <Select
          label="Language"
          value={settings.locale || "en-US"}
          onValueChange={(v) => mutate({ locale: v })}
          disabled={isPending}
        >
          <Option value="en-US">English (US)</Option>
        </Select>
      </SettingsRow>
    </Card>
  );
}
