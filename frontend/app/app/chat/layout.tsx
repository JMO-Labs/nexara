/**
 * @file app/app/chat/layout.tsx
 * @brief Cancels Shell main padding so the chat fills the viewport below the
 *        top bar (and above the phone tab bar).
 */
import type { ReactNode } from "react";

export default function ChatRouteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="-mx-4 flex h-[calc(100dvh-3.5rem-84px-env(safe-area-inset-bottom))] min-h-0 md:-mx-8 md:h-[calc(100dvh-3.5rem)]">
      {children}
    </div>
  );
}
