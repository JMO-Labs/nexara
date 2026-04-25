'use client';
/**
 * @file app/app/chat/page.tsx
 * @brief Chat root: channel list + empty thread pane (desktop) /
 *        channel list only (mobile).
 */
import { ChatLayout } from '@/components/chat/ChatLayout';

export default function ChatIndexPage() {
  return <ChatLayout activeId={null} />;
}
