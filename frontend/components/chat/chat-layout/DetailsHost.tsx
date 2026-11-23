"use client";
/**
 * @file components/chat/chat-layout/DetailsHost.tsx
 * @brief Places the details body: inline aside at xl+, otherwise a right
 *        slide-over (focus-trapped, Esc closes, focus returns to the toggle).
 */
import { Drawer } from "@/components/ui/Drawer";
import { DetailsPane } from "../details/DetailsPane";

export const DETAILS_ID = "chat-details";
export const DETAILS_TOGGLE_ID = "chat-details-toggle";

export interface DetailsHostProps {
  channelId: string;
  inline: boolean;
  open: boolean;
  onClose: () => void;
}

/**
 * @param props see DetailsHostProps
 * @return aside, drawer or null
 */
export function DetailsHost({
  channelId,
  inline,
  open,
  onClose,
}: DetailsHostProps) {
  if (!open) return null;
  if (inline) {
    return (
      <aside
        id={DETAILS_ID}
        aria-label="Details"
        className="glass flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[32px]"
      >
        <h2 className="shrink-0 px-5 pt-4 text-base font-semibold">Details</h2>
        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          <DetailsPane channelId={channelId} />
        </div>
      </aside>
    );
  }
  // Return focus to the header toggle explicitly (Safari does not focus
  // buttons on click, so the dialog's own restore can land on <body>).
  const close = () => {
    onClose();
    setTimeout(() => document.getElementById(DETAILS_TOGGLE_ID)?.focus(), 0);
  };
  return (
    <Drawer open onClose={close} title="Details" side="right">
      <div id={DETAILS_ID}>
        <DetailsPane channelId={channelId} />
      </div>
    </Drawer>
  );
}
