"use client";
/**
 * @file components/chat/TypingIndicator.tsx
 * @brief Subtle "X is typing…" line shown above the composer.
 */

export interface TypingIndicatorProps {
  count: number;
}

/**
 * @brief Typing line; renders nothing when nobody types.
 * @param count number of people typing
 * @return status line or null
 */
export function TypingIndicator({ count }: TypingIndicatorProps) {
  if (count <= 0) return null;
  const text =
    count === 1 ? "Someone is typing…" : `${count} people are typing…`;
  return (
    <p role="status" className="px-4 py-1 text-xs text-muted italic">
      {text}
    </p>
  );
}
