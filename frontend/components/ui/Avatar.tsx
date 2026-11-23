/**
 * @file components/ui/Avatar.tsx
 * @brief Avatar with colored-initials fallback, plus overlapping AvatarGroup.
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import { useOnline } from "@/stores/presence";

const sizes = {
  sm: "size-6 text-[10px]",
  md: "size-8 text-xs",
  lg: "size-12 text-base",
};

export interface AvatarProps {
  src?: string;
  /** Missing for deleted/unknown users; falls back to "?". */
  name?: string;
  size?: keyof typeof sizes;
  className?: string;
  /** When set, watches presence and shows an online dot. */
  userId?: string;
}

/**
 * Initials fills: the Aegean door palette, darkened where needed so white
 * initials pass AA (4.5:1) in both themes.
 */
export const AVATAR_COLORS = [
  "#2F5873",
  "#A8505F",
  "#5A6B3A",
  "#8F6A26",
  "#3F6A86",
  "#7D5A7A",
  "#55636D",
] as const;

/**
 * @brief Stable "random" color for a person: same name, same color everywhere.
 * @param seed name (or id)
 * @return hex fill
 */
export function avatarColor(seed: string | undefined): string {
  let h = 0;
  for (const ch of seed ?? "") h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

/**
 * @brief Compute up to two initials.
 * @param name display name
 * @return uppercase initials
 */
function initials(name: string | undefined): string {
  return (name ?? "")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

/**
 * @brief Round avatar; image when `src`, else initials. Online dot when `userId` is online.
 * @param src image url
 * @param name person name (alt text + initials)
 * @return avatar element
 */
export function Avatar({
  src,
  name,
  size = "md",
  className,
  userId,
}: AvatarProps) {
  const [failed, setFailed] = React.useState(false);
  const online = useOnline(userId);
  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white",
        sizes[size],
        className,
      )}
      style={{ background: avatarColor(name) }}
    >
      {src && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element -- user/external URL, unknown host for next/image
        <img
          src={src}
          alt={name ?? ""}
          className="size-full rounded-full object-cover"
          onError={() => setFailed(true)}
        />
      ) : (
        <span role="img" aria-label={name ?? "Unknown user"}>
          {initials(name) || "?"}
        </span>
      )}
      {online && (
        // Static on purpose: no animation, so nothing to reduce for motion.
        <span
          data-testid="online-dot"
          className="bg-ok ring-surface absolute right-0 bottom-0 size-1/4 rounded-full ring-2"
        >
          <span className="sr-only">online</span>
        </span>
      )}
    </span>
  );
}

export interface AvatarGroupProps {
  max?: number;
  children: React.ReactNode;
}

/**
 * @brief Overlapping avatars; extras collapse to "+N".
 * @param max visible count (default 4)
 * @return group element
 */
export function AvatarGroup({ max = 4, children }: AvatarGroupProps) {
  const items = React.Children.toArray(children);
  const extra = items.length - max;
  return (
    <div className="flex -space-x-2 [&>*]:ring-2 [&>*]:ring-surface">
      {items.slice(0, max)}
      {extra > 0 && (
        <span className="inline-flex size-8 items-center justify-center rounded-full bg-bg text-xs font-semibold text-ink">
          +{extra}
        </span>
      )}
    </div>
  );
}

export default Avatar;
