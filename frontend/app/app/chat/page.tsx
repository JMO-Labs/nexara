"use client";
/**
 * @file app/app/chat/page.tsx
 * @brief Chat root: channel list (full screen on phone) / empty thread pane.
 */
import { ChatLayout } from "@/components/chat/ChatLayout";

export default function ChatIndexPage() {
  return <ChatLayout activeId={null} />;
}
