"use client";
/**
 * @file app/app/chat/page.tsx
 * @brief Chat root: channel list (full screen on phone) / empty thread pane.
 *        `?dm=<userId>` opens (or creates) the DM with that member.
 */
import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChatLayout } from "@/components/chat/ChatLayout";
import { useCreateDm } from "@/hooks/useChat";

export default function ChatIndexPage() {
  const router = useRouter();
  const dm = useSearchParams().get("dm");
  const { mutateAsync } = useCreateDm();
  useEffect(() => {
    if (!dm) return;
    mutateAsync(dm)
      .then((ch) => router.replace(`/app/chat/${ch.id}`))
      .catch(() => router.replace("/app/chat"));
  }, [dm, mutateAsync, router]);
  return <ChatLayout activeId={null} />;
}
