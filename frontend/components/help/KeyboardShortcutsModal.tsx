"use client";
/**
 * @file components/help/KeyboardShortcutsModal.tsx
 * @brief Modal displaying available keyboard shortcuts in sections.
 */
import { Modal } from "@/components/ui";
import { useModals } from "@/stores/modals";

interface Shortcut {
  keys: string;
  action: string;
}

interface ShortcutSection {
  name: string;
  shortcuts: Shortcut[];
}

const SHORTCUTS: ShortcutSection[] = [
  {
    name: "Navigation",
    shortcuts: [
      { keys: "Ctrl+K", action: "Open command palette" },
      { keys: "?", action: "Open this help" },
    ],
  },
  {
    name: "Actions",
    shortcuts: [
      { keys: "Enter", action: "Send message" },
      { keys: "Shift+Enter", action: "New line in message" },
      { keys: "Esc", action: "Close modal or popover" },
    ],
  },
  {
    name: "Gallery",
    shortcuts: [
      { keys: "←", action: "Previous image" },
      { keys: "→", action: "Next image" },
      { keys: "Esc", action: "Close lightbox" },
    ],
  },
];

/**
 * @brief Keyboard shortcuts dialog driven by the modals store.
 * @return modal element
 */
export function KeyboardShortcutsModal() {
  const open = useModals((s) => s.keyboardShortcutsOpen);
  const setOpen = useModals((s) => s.setKeyboardShortcutsOpen);

  return (
    <Modal
      open={open}
      onClose={() => setOpen(false)}
      title="Keyboard shortcuts"
    >
      <div className="flex flex-col gap-6">
        {SHORTCUTS.map((section) => (
          <section key={section.name} className="flex flex-col gap-3">
            <h3 className="text-muted text-xs font-semibold tracking-wider uppercase">
              {section.name}
            </h3>
            <ul className="flex flex-col gap-2">
              {section.shortcuts.map((shortcut, idx) => (
                <li
                  key={idx}
                  className="flex items-center justify-between gap-4"
                >
                  <span className="text-sm">{shortcut.action}</span>
                  <kbd className="bg-surface-strong text-accent rounded px-2 py-1 font-mono text-xs whitespace-nowrap">
                    {shortcut.keys}
                  </kbd>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </Modal>
  );
}

export default KeyboardShortcutsModal;
