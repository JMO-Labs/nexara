/**
 * @file app/app/chat/layout.tsx
 * @brief Makes the chat fill the viewport height below the top bar (and above
 *        the phone tab bar), inside the Shell frame.
 */
import type { ReactNode } from "react";

export default function ChatRouteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-[calc(100dvh-3.5rem-84px-env(safe-area-inset-bottom))] min-h-0 pb-4 md:h-[calc(100dvh-5rem)]">
      {children}
    </div>
  );
}
