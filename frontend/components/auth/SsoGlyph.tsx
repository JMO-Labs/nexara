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
 * @brief Inline SVG data URI for a mark (the letter lives in an image, so it
 *        never joins the link's DOM text or accessible name).
 * @param mark letter + brand colour
 * @return CSS url() value
 */
function markUrl(mark: { letter: string; color: string }): string {
  const size = mark.letter.length > 1 ? 9 : 12;
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">` +
    `<rect width="20" height="20" rx="4" fill="${mark.color}"/>` +
    `<text x="10" y="14" text-anchor="middle" font-size="${size}" font-weight="700" ` +
    `fill="#fff" font-family="system-ui, sans-serif">${mark.letter}</text></svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

/**
 * @brief Brand glyph for a preset; generic key icon otherwise. aria-hidden,
 *        no DOM text.
 * @param preset provider preset key (nullable)
 * @return decorative span
 */
export function SsoGlyph({ preset }: { preset?: string | null }) {
  const mark = preset ? MARKS[preset] : undefined;
  if (!mark) return <KeyRound aria-hidden="true" className="size-5" />;
  return (
    <span
      aria-hidden="true"
      className="inline-block size-5 shrink-0 bg-contain bg-no-repeat"
      style={{ backgroundImage: markUrl(mark) }}
      data-testid={`sso-glyph-${preset}`}
    />
  );
}
