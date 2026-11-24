/**
 * @file components/auth/SsoGlyph.tsx
 * @brief Decorative per-preset brand mark for SSO buttons (inline SVG).
 */
import { KeyRound } from "lucide-react";

const MARKS: Record<string, { letter: string; color: string }> = {
  google: { letter: "G", color: "#4285F4" },
  microsoft: { letter: "M", color: "#00A4EF" },
  github: { letter: "GH", color: "#24292F" },
  gitlab: { letter: "GL", color: "#FC6D26" },
  discord: { letter: "D", color: "#5865F2" },
  authentik: { letter: "A", color: "#FD4B2D" },
  keycloak: { letter: "K", color: "#4D4D4D" },
  authelia: { letter: "Au", color: "#2563EB" },
};

/**
 * @brief Brand glyph for a preset; generic key icon otherwise. aria-hidden.
 * @param preset provider preset key (nullable)
 * @return decorative svg
 */
export function SsoGlyph({ preset }: { preset?: string | null }) {
  const mark = preset ? MARKS[preset] : undefined;
  if (!mark) return <KeyRound aria-hidden="true" className="size-5" />;
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 20 20"
      className="size-5"
      data-testid={`sso-glyph-${preset}`}
    >
      <rect width="20" height="20" rx="4" fill={mark.color} />
      <text
        x="10"
        y="14"
        textAnchor="middle"
        fontSize={mark.letter.length > 1 ? 9 : 12}
        fontWeight="700"
        fill="#fff"
        fontFamily="system-ui, sans-serif"
      >
        {mark.letter}
      </text>
    </svg>
  );
}
