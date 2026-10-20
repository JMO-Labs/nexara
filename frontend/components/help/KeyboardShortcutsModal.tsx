"use client";
/**
 * @file components/help/KeyboardShortcutsModal.tsx
 * @brief Modal displaying available keyboard shortcuts in sections.
 */
import * as React from "react";
import Modal from "@mui/joy/Modal";
import ModalDialog from "@mui/joy/ModalDialog";
import ModalClose from "@mui/joy/ModalClose";
import Typography from "@mui/joy/Typography";
import Stack from "@mui/joy/Stack";
import Box from "@mui/joy/Box";
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

export function KeyboardShortcutsModal() {
  const open = useModals((s) => s.keyboardShortcutsOpen);
  const setOpen = useModals((s) => s.setKeyboardShortcutsOpen);

  return (
    <Modal open={open} onClose={() => setOpen(false)}>
      <ModalDialog sx={{ maxWidth: 480, p: 0 }}>
        <ModalClose variant="plain" sx={{ m: 1 }} />
        <Stack spacing={3} sx={{ p: 3, pt: 2 }}>
          <Typography component="h2" level="title-lg">
            Keyboard Shortcuts
          </Typography>
          {SHORTCUTS.map((section) => (
            <Stack key={section.name} spacing={1.5}>
              <Typography
                level="title-sm"
                sx={{ textTransform: "uppercase", letterSpacing: "0.05em" }}
              >
                {section.name}
              </Typography>
              <Stack spacing={1}>
                {section.shortcuts.map((shortcut, idx) => (
                  <Box
                    key={idx}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 2,
                    }}
                  >
                    <Typography level="body-sm">{shortcut.action}</Typography>
                    <Box
                      component="kbd"
                      sx={{
                        px: 0.75,
                        py: 0.375,
                        borderRadius: 4,
                        fontSize: 12,
                        bgcolor: "neutral.softBg",
                        color: "neutral.softColor",
                        fontFamily: "monospace",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {shortcut.keys}
                    </Box>
                  </Box>
                ))}
              </Stack>
            </Stack>
          ))}
        </Stack>
      </ModalDialog>
    </Modal>
  );
}

export default KeyboardShortcutsModal;
