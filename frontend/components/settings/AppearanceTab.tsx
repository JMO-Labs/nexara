"use client";
/**
 * @file components/settings/AppearanceTab.tsx
 * @brief Appearance settings tab: theme (radio group) and language.
 */
import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { SettingsRow, Select, Option, Switch } from "@/components/ui";
import { Panel, Segmented } from "@/components/ui/page";
import { useUI } from "@/stores/ui";
import { cn } from "@/lib/utils";
import type { UserSettings } from "@/lib/api/settings";
import { PatternPicker } from "./PatternPicker";
import { useFeature } from "@/hooks/useFeature";
import { useUpdateSettings, useUserSettings } from "@/hooks/useSettings";

type FontSize = UserSettings["font_size"];
type Theme = (typeof THEMES)[number]["value"];
type Density = (typeof DENSITIES)[number]["value"];

const THEMES = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
] as const;

const DENSITIES = [
  { value: "comfortable", label: "Comfortable" },
  { value: "compact", label: "Compact" },
] as const;

const FONT_SIZES = [
  { value: "small", label: "Small", cls: "text-xs" },
  { value: "medium", label: "Medium", cls: "text-sm" },
  { value: "large", label: "Large", cls: "text-base" },
] as const;

/** @brief No-op subscribe for the static mounted snapshot. */
const noopSubscribe = () => () => {};

/**
 * @brief Theme, font size, compact feed and language preferences.
 * @return appearance tab content
 */
export function AppearanceTab() {
  const { theme, setTheme } = useTheme();
  const { data: settings } = useUserSettings();
  const { mutate, isPending } = useUpdateSettings();
  const simpleOn = useFeature("simple_mode");
  const density = useUI((s) => s.density);
  const setDensity = useUI((s) => s.setDensity);
  // SSR-safe mount detection for next-themes: false on server, true on client.
  const mounted = useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );

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
    <Panel title="Appearance">
      <SettingsRow
        label="Theme"
        description="Choose light, dark, or follow your device."
      >
        <Segmented<Theme>
          label="Theme"
          value={(theme || "system") as Theme}
          onChange={onTheme}
          options={THEMES.map(({ value, label }) => ({ value, label }))}
        />
      </SettingsRow>

      <SettingsRow label="Font size" description="Text size in the app.">
        <Segmented<FontSize>
          label="Font size"
          value={settings.font_size}
          onChange={(v) => mutate({ font_size: v })}
          options={FONT_SIZES.map(({ value, label }) => ({ value, label }))}
        />
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

      <SettingsRow
        label="Background pattern"
        description="Pattern behind your home page."
      >
        <PatternPicker
          label="Background pattern"
          value={settings.home_pattern ?? null}
          onChange={(v) => mutate({ home_pattern: v })}
          allowDefault
          disabled={isPending}
        />
      </SettingsRow>

      <SettingsRow
        label="Reduce transparency"
        description="Makes panels solid. Easier to read on busy backgrounds."
      >
        <Switch
          aria-label="Reduce transparency"
          checked={settings.reduce_transparency ?? false}
          onCheckedChange={(v) => mutate({ reduce_transparency: v })}
          disabled={isPending}
        />
      </SettingsRow>

      {simpleOn && (
        <SettingsRow
          label="Simple mode"
          description="Bigger text and buttons, and only Home, Photos, Family and Calendar in the menu."
        >
          <Switch
            aria-label="Simple mode"
            checked={settings.simple_mode ?? false}
            onCheckedChange={(v) => mutate({ simple_mode: v })}
            disabled={isPending}
          />
        </SettingsRow>
      )}

      <SettingsRow label="Preview" description="How your choices look.">
        <div
          data-testid="appearance-preview"
          data-font-size={settings.font_size}
          aria-live="polite"
          className={cn(
            "glass-item rounded-[20px] p-3",
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
        label="Density"
        description="Comfortable keeps today's spacing; Compact fits more on screen."
      >
        <Segmented<Density>
          label="Density"
          value={density as Density}
          onChange={(v) => setDensity(v)}
          options={DENSITIES.map(({ value, label }) => ({ value, label }))}
        />
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
    </Panel>
  );
}
