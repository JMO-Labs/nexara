/**
 * @file components/help/HelpButton.tsx
 * @brief Floating help button with quick access menu.
 *
 * Provides shortcuts to keyboard shortcuts, docs, and support.
 */

"use client";

import { CircleHelp } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/shadcn/dropdown-menu";
import { useModals } from "@/stores/modals";

/**
 * @brief Fixed bottom-right help menu trigger.
 * @return dropdown menu element
 */
export function HelpButton() {
  const setKeyboardShortcutsOpen = useModals((s) => s.setKeyboardShortcutsOpen);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Help menu"
        className="bg-surface-strong text-accent focus-visible:outline-accent fixed right-5 bottom-5 z-[1000] flex size-12 items-center justify-center rounded-full shadow-md transition-transform outline-none hover:scale-110 focus-visible:outline-2 focus-visible:outline-offset-2 motion-reduce:transition-none motion-reduce:hover:scale-100"
      >
        <CircleHelp size={24} aria-hidden="true" />
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side="top"
        align="end"
        className="bg-surface text-ink min-w-[200px]"
      >
        <DropdownMenuItem onSelect={() => setKeyboardShortcutsOpen(true)}>
          Keyboard shortcuts
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <a href="/docs" target="_blank" rel="noopener">
            Documentation
          </a>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <a href="/contact" target="_blank" rel="noopener">
            Contact support
          </a>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
