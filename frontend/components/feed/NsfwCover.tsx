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
}

/**
 * @brief Wrap content; when NSFW show it blurred under a tap-to-view cover.
 * @param nsfw whether the item is NSFW
 * @param itemId session-reveal key
 * @return children, covered if needed
 */
export function NsfwCover(props: NsfwCoverProps) {
  // Outer gate keeps non-NSFW content free of query hooks/providers.
  return props.nsfw ? <Covered {...props} /> : <>{props.children}</>;
}

function Covered({ nsfw, itemId, children, className }: NsfwCoverProps) {
  const { data } = useUserSettings();
  const [shown, setShown] = React.useState(() => revealed.has(itemId));
  if (!nsfw || shown || data?.always_show_nsfw) return <>{children}</>;
  return (
    <div className={`relative overflow-hidden ${className ?? ""}`}>
      <div aria-hidden="true" inert style={{ filter: "blur(24px)" }}>
        {children}
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
          className="rounded-full border border-ink/20 px-4 py-2 text-sm font-semibold text-ink outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          NSFW — tap to view
        </button>
      </div>
    </div>
  );
}

export default NsfwCover;
