"use client";
/**
 * @file components/layout/SimpleModeOffRow.tsx
 * @brief "Turn off simple mode" row for the More sheet (mounted only while
 *        simple mode is on, so the sheet needs no settings hooks otherwise).
 */
import { ZoomOut } from "lucide-react";
import { useUpdateSettings } from "@/hooks/useSettings";

/**
 * @param props onClose closes the host sheet
 * @return list item with the action button
 */
export function SimpleModeOffRow({ onClose }: { onClose: () => void }) {
  const { mutate } = useUpdateSettings();
  return (
    <li>
      <button
        type="button"
        className="text-ink flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left hover:bg-[var(--nx-item)]"
        onClick={() => {
          mutate({ simple_mode: false });
          onClose();
        }}
      >
        <ZoomOut aria-hidden className="size-5" />
        <span>Turn off simple mode</span>
      </button>
    </li>
  );
}
