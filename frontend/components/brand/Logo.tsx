/**
 * @file Logo.tsx
 * @brief Nexara brand mark, wordmark and lockup.
 */
import { cn } from "@/lib/utils";

const circle = (cx: number, cy: number, r: number, n: 1 | 2 | 3) => ({
  cx,
  cy,
  r,
  fill: `var(--nx-logo-${n})`,
  style: {
    fillOpacity: "var(--nx-logo-fo)",
    mixBlendMode: "var(--nx-logo-blend)",
  } as unknown as React.CSSProperties,
});

/**
 * @brief Inline SVG logo mark driven by --nx-logo-* tokens.
 * @param size Pixel size (square).
 * @param className Extra classes.
 */
export function LogoMark({
  size = 32,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 512 512"
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <g style={{ isolation: "isolate" }}>
        <circle {...circle(256, 176, 140, 1)} />
        <circle {...circle(152, 342, 118, 2)} />
        <circle {...circle(360, 342, 118, 3)} />
      </g>
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth={30}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M70 240 L256 96 L442 240" />
        <path d="M128 196 V366 Q128 398 160 398 H352 Q384 398 384 366 V196" />
        <path d="M200 352 V228 L312 352 V228" />
      </g>
    </svg>
  );
}

/**
 * @brief Two-weight "nexara" wordmark.
 * @param className Extra classes.
 */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("font-semibold", className)}>
      nex<span className="font-light">ara</span>
    </span>
  );
}

/**
 * @brief Logo lockup: custom image when logoUrl set, else mark + wordmark.
 * @param logoUrl Optional custom logo URL.
 * @param name Accessible name.
 * @param size Mark/image pixel size.
 */
export function BrandLockup({
  logoUrl,
  name,
  size = 32,
}: {
  logoUrl?: string | null;
  name: string;
  size?: number;
}) {
  if (logoUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={logoUrl} alt={name} height={size} style={{ height: size }} />
    );
  }
  return (
    <span className="inline-flex items-center gap-2" aria-label={name}>
      <LogoMark size={size} />
      <Wordmark />
    </span>
  );
}
