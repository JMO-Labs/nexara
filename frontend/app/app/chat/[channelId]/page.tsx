"use client";
/**
 * @file app/app/chat/[channelId]/page.tsx
 * @brief Active conversation. Channel + DM share the same UUID space, so
 *        a single dynamic segment serves both.
 */
import { use } from "react";
import { ChatLayout } from "@/components/chat/ChatLayout";

export default function ChatThreadPage({
  params,
}: {
  params: Promise<{ channelId: string }>;
}) {
  const { channelId } = use(params);
  return <ChatLayout activeId={channelId} />;
}
