"use client";
/**
 * @file components/audio/AudioPlayer.tsx
 * @brief Native `<audio controls>` plus a 1x / 1.5x speed toggle.
 */
import * as React from "react";

/**
 * @brief Voice note / story player.
 * @param src audio file URL
 * @param label accessible name for the player
 * @return player element
 */
export function AudioPlayer({
  src,
  label = "Voice note",
}: {
  src: string;
  label?: string;
}) {
  const ref = React.useRef<HTMLAudioElement>(null);
  const [fast, setFast] = React.useState(false);
  React.useEffect(() => {
    if (ref.current) ref.current.playbackRate = fast ? 1.5 : 1;
  }, [fast]);
  return (
    <div className="flex items-center gap-2">
      <audio
        ref={ref}
        src={src}
        controls
        preload="metadata"
        aria-label={label}
        className="h-11 min-w-0 flex-1"
      />
      <button
        type="button"
        aria-pressed={fast}
        aria-label="Play at 1.5 times speed"
        onClick={() => setFast((f) => !f)}
        className="min-h-11 min-w-11 rounded-full px-3 text-sm font-medium text-ink outline-none hover:bg-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent aria-pressed:bg-surface-strong aria-pressed:text-bg"
      >
        {fast ? "1.5×" : "1×"}
      </button>
    </div>
  );
}

export default AudioPlayer;
