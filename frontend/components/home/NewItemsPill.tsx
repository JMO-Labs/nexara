/**
 * @file components/home/NewItemsPill.tsx
 * @brief Floating "N new" pill shown under the top bar when feed items are buffered.
 */
import * as React from "react";

export interface NewItemsPillProps {
  count: number;
  onClick: () => void;
}

/**
 * @brief Pill button announcing buffered feed items.
 * @param count number of pending items
 * @param onClick reveal handler
 * @return pill or null when count is 0
 */
export function NewItemsPill({ count, onClick }: NewItemsPillProps) {
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 top-16 z-30 flex justify-center"
    >
      {count > 0 && (
        <button
          type="button"
          onClick={onClick}
          className="pointer-events-auto rounded-full bg-accent px-4 py-1.5 text-sm font-semibold text-surface-strong shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          {count} new
        </button>
      )}
    </div>
  );
}

export default NewItemsPill;
