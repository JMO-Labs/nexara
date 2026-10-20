/**
 * @file HelpButton.tsx
 * @brief Floating help button with quick access menu.
 *
 * Provides shortcuts to tour, keyboard shortcuts, docs, and support.
 */

"use client";

import Box from "@mui/joy/Box";
import Menu from "@mui/joy/Menu";
import MenuItem from "@mui/joy/MenuItem";
import Dropdown from "@mui/joy/Dropdown";
import MenuButton from "@mui/joy/MenuButton";
import ListDivider from "@mui/joy/ListDivider";
import { QuestionMarkCircleIcon } from "@heroicons/react/24/outline";
import { useModals } from "@/stores/modals";

export function HelpButton() {
  const setKeyboardShortcutsOpen = useModals((s) => s.setKeyboardShortcutsOpen);

  return (
    <Dropdown>
      <MenuButton
        slots={{ root: "button" }}
        slotProps={{
          root: {
            "aria-label": "Help menu",
            "aria-haspopup": "menu",
            style: {
              background: "transparent",
              border: 0,
              padding: 4,
              cursor: "pointer",
            },
          },
        }}
      >
        <Box
          sx={{
            position: "fixed",
            bottom: 20,
            right: 20,
            width: 48,
            height: 48,
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "primary.main",
            color: "white",
            cursor: "pointer",
            boxShadow: "md",
            transition: "all 0.2s ease",
            "&:hover": {
              transform: "scale(1.1)",
            },
            zIndex: 1000,
          }}
        >
          <QuestionMarkCircleIcon width={24} height={24} />
        </Box>
      </MenuButton>
      <Menu placement="top-end" sx={{ minWidth: 200 }}>
        <MenuItem onClick={() => setKeyboardShortcutsOpen(true)}>
          Keyboard shortcuts
        </MenuItem>
        <ListDivider />
        <MenuItem component="a" href="/docs" target="_blank" rel="noopener">
          Documentation
        </MenuItem>
        <MenuItem component="a" href="/contact" target="_blank" rel="noopener">
          Contact support
        </MenuItem>
      </Menu>
    </Dropdown>
  );
}
