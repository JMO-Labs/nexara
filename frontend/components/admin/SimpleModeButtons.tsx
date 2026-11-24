"use client";
/**
 * @file components/admin/SimpleModeButtons.tsx
 * @brief Admin row actions: turn a user's simple mode on or off.
 */
import { ZoomIn, ZoomOut } from "lucide-react";
import { IconButton } from "@/components/ui";

/**
 * @brief Simple mode on/off icon buttons.
 * @param onToggle called with the requested state
 * @return button pair
 */
export function SimpleModeButtons({
  onToggle,
}: {
  onToggle: (on: boolean) => void;
}) {
  return (
    <>
      <IconButton
        variant="glass"
        aria-label="Turn on simple mode"
        tooltip="Turn on simple mode"
        onClick={() => onToggle(true)}
      >
        <ZoomIn className="size-4" aria-hidden="true" />
      </IconButton>
      <IconButton
        variant="glass"
        aria-label="Turn off simple mode"
        tooltip="Turn off simple mode"
        onClick={() => onToggle(false)}
      >
        <ZoomOut className="size-4" aria-hidden="true" />
      </IconButton>
    </>
  );
}
