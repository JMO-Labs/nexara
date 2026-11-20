"use client";
/**
 * @file components/settings/HelpTab.tsx
 * @brief Settings Help section: opens the keyboard shortcuts modal.
 */
import { Button } from "@/components/ui";
import { useModals } from "@/stores/modals";

/**
 * @brief Help settings body.
 * @return heading, one-line intro and shortcuts button
 */
export function HelpTab() {
  const setKeyboardShortcutsOpen = useModals((s) => s.setKeyboardShortcutsOpen);
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-ink">Help</h2>
      <p className="text-muted text-sm">
        Browse the keyboard shortcuts available across Nexara.
      </p>
      <div>
        <Button onClick={() => setKeyboardShortcutsOpen(true)}>
          Keyboard shortcuts
        </Button>
      </div>
    </div>
  );
}
