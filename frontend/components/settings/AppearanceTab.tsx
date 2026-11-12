"use client";
/**
 * @file components/settings/AppearanceTab.tsx
 * @brief Appearance settings tab: theme (radio group) and language.
 */
import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Card, SettingsRow, Select, Option } from "@/components/ui";
import { RadioGroup, RadioGroupItem } from "@/components/ui/shadcn/radio-group";
import { useUI } from "@/stores/ui";
import { useUpdateSettings, useUserSettings } from "@/hooks/useSettings";

const THEMES = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
] as const;

const DENSITIES = [
  { value: "comfortable", label: "Comfortable" },
  { value: "compact", label: "Compact" },
] as const;

/**
 * @brief Theme and language preferences.
 * @return appearance tab content
 */
export function AppearanceTab() {
  const { theme, setTheme } = useTheme();
  const { data: settings } = useUserSettings();
  const { mutate, isPending } = useUpdateSettings();
  const density = useUI((s) => s.density);
  const setDensity = useUI((s) => s.setDensity);
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

      <SettingsRow
        label="Density"
        description="Comfortable keeps today's spacing; Compact fits more on screen."
      >
        <RadioGroup
          aria-label="Density"
          value={density}
          onValueChange={(v) => setDensity(v as "comfortable" | "compact")}
        >
          {DENSITIES.map(({ value, label }) => (
            <label
              key={value}
              htmlFor={`density-${value}`}
              className="flex min-h-11 items-center gap-3 text-sm"
            >
              <RadioGroupItem id={`density-${value}`} value={value} />
              {label}
            </label>
          ))}
        </RadioGroup>
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
