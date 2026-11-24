"use client";
/**
 * @file components/feed/NsfwCover.tsx
 * @brief Blur + solid cover over NSFW content. Reveal is remembered per item
 *        for the session; skipped when the viewer sets always_show_nsfw.
 *        No backdrop-filter: the content itself is blurred.
 */
import * as React from "react";
import { useUserSettings } from "@/hooks/useSettings";

const revealed = new Set<string>();

/** @brief Forget all reveals (tests). */
export const resetRevealed = () => revealed.clear();

export interface NsfwCoverProps {
  nsfw?: boolean;
  /** Stable id (post/media/gallery) so a reveal persists in the session. */
  itemId: string;
  children: React.ReactNode;
  className?: string;
  /** Small tiles: short "NSFW" label (aria-label unchanged). */
  compact?: boolean;
  /** Do not mount children while covered (e.g. autoplaying video). */
  hideWhenCovered?: boolean;
  /** Reports whether the content is currently covered. */
  onCovered?: (covered: boolean) => void;
}

/**
 * @brief Wrap content; when NSFW show it blurred under a tap-to-view cover.
 * @param nsfw whether the item is NSFW
 * @param itemId session-reveal key
 * @return children, covered if needed
 */
export function NsfwCover(props: NsfwCoverProps) {
  // Outer gate keeps non-NSFW content free of query hooks/providers.
  return props.nsfw ? <Covered {...props} /> : <Plain {...props} />;
}

function Plain({ children, onCovered }: NsfwCoverProps) {
  React.useEffect(() => onCovered?.(false), [onCovered]);
  return <>{children}</>;
}

function Covered({
  itemId,
  children,
  className,
  compact,
  hideWhenCovered,
  onCovered,
}: NsfwCoverProps) {
  const { data } = useUserSettings();
  const [shown, setShown] = React.useState(() => revealed.has(itemId));
  const covered = !(shown || data?.always_show_nsfw);
  React.useEffect(() => onCovered?.(covered), [onCovered, covered]);
  if (!covered) return <>{children}</>;
  return (
    <div className={`relative overflow-hidden ${className ?? ""}`}>
      <div aria-hidden="true" inert style={{ filter: "blur(24px)" }}>
        {hideWhenCovered ? <div className="size-full min-h-24" /> : children}
      </div>
      <div className="absolute inset-0 flex items-center justify-center bg-[var(--nx-glass-solid)]">
        <button
          type="button"
          aria-label="Show NSFW content"
          onClick={(e) => {
            e.stopPropagation();
            revealed.add(itemId);
            setShown(true);
          }}
          className={`rounded-full border border-ink/20 font-semibold text-ink outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${compact ? "px-2 py-1 text-xs" : "px-4 py-2 text-sm"}`}
        >
          {compact ? "NSFW" : "NSFW — tap to view"}
        </button>
      </div>
    </div>
  );
}

export default NsfwCover;
