"use client";
/**
 * @file components/settings/HelpTab.tsx
 * @brief Settings Help section: opens the keyboard shortcuts modal.
 */
import { Button } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { SettingsRow } from "@/components/ui/SettingsRow";
import { useModals } from "@/stores/modals";

/**
 * @brief Help settings body.
 * @return panel with a keyboard shortcuts row
 */
export function HelpTab() {
  const setKeyboardShortcutsOpen = useModals((s) => s.setKeyboardShortcutsOpen);
  return (
    <Panel title="Help">
      <SettingsRow
        label="Keyboard shortcuts"
        description="Browse the keyboard shortcuts available across Nexara."
      >
        <Button
          variant="secondary"
          onClick={() => setKeyboardShortcutsOpen(true)}
        >
          Keyboard shortcuts
        </Button>
      </SettingsRow>
    </Panel>
  );
}
