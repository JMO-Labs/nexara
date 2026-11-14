/**
 * @file components/ui/Avatar.tsx
 * @brief Avatar with initials fallback, plus overlapping AvatarGroup.
 */
import * as React from "react";
import { cn } from "@/lib/utils";

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
 * @brief Round avatar; image when `src`, else initials.
 * @param src image url
 * @param name person name (alt text + initials)
 * @return avatar element
 */
export function Avatar({ src, name, size = "md", className }: AvatarProps) {
  const [failed, setFailed] = React.useState(false);
  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-accent font-semibold text-surface-strong",
        sizes[size],
        className,
      )}
    >
      {src && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element -- user/external URL, unknown host for next/image
        <img
          src={src}
          alt={name ?? ""}
          className="size-full object-cover"
          onError={() => setFailed(true)}
        />
      ) : (
        <span role="img" aria-label={name ?? "Unknown user"}>
          {initials(name) || "?"}
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
