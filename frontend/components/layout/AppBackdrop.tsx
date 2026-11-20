"use client";
/**
 * @file components/layout/AppBackdrop.tsx
 * @brief Fixed brand gradient plus optional pattern mask behind the app.
 */
import { useUserSettings } from "@/hooks/useSettings";
import { useBranding } from "@/hooks/useBranding";
import { patternUrl, type HomePattern } from "@/lib/patterns";

/**
 * @brief App backdrop; pattern = user setting, else community default, else contour.
 * @return decorative fixed layer
 */
export function AppBackdrop() {
  const { data: settings } = useUserSettings();
  const { data: branding } = useBranding();
  const pattern: HomePattern =
    (settings as { home_pattern?: HomePattern | null } | undefined)
      ?.home_pattern ??
    (branding as { home_pattern?: HomePattern | null } | undefined)
      ?.home_pattern ??
    "contour";
  const url = patternUrl(pattern);
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-bg"
    >
      <div
        className="absolute -inset-20 opacity-80"
        style={{
          filter: "blur(46px)",
          background:
            "radial-gradient(38% 40% at 12% 18%, var(--nx-blue), transparent 70%), radial-gradient(30% 34% at 88% 82%, var(--nx-red), transparent 70%), radial-gradient(30% 30% at 70% 15%, color-mix(in srgb, var(--nx-blue) 50%, var(--nx-bg)), transparent 70%)",
        }}
      />
      {url && (
        <div
          data-pattern={pattern}
          className="absolute inset-0"
          style={{
            background: "var(--nx-pattern)",
            WebkitMask: `${url} repeat`,
            mask: `${url} repeat`,
          }}
        />
      )}
    </div>
  );
}
