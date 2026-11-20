"use client";
/**
 * @file app/app/page.tsx
 * @brief Home: glass bento (feed, chats, up next, photos) with scope + accordion.
 */
import { useSession } from "@/stores/session";
import { useHomeChats } from "@/hooks/useHomeChats";
import { useHomeAccordion } from "@/hooks/useHomeAccordion";
import { Greeting } from "@/components/home/Greeting";
import { ScopeBar } from "@/components/home/ScopeBar";
import { PeopleStrip } from "@/components/home/PeopleStrip";
import { NeedsChips } from "@/components/home/NeedsChips";
import { FeedTile } from "@/components/home/tiles/FeedTile";
import { ChatsTile } from "@/components/home/tiles/ChatsTile";
import { UpNextTile } from "@/components/home/tiles/UpNextTile";
import { PhotosTile } from "@/components/home/tiles/PhotosTile";

/**
 * @brief Home page.
 * @return page element
 */
export default function AppHome() {
  const user = useSession((s) => s.user);
  const name = user?.display_name ?? user?.username ?? "there";
  const { data } = useHomeChats();
  const mention = (data?.items ?? []).some((t) => t.mentions_me);
  const { open, toggle } = useHomeAccordion(mention ? "chat" : "next");
  return (
    <div className="mx-auto w-full max-w-[1400px] px-4 py-6 md:px-6">
      <div className="mb-4 flex flex-col gap-3.5 md:flex-row md:items-end md:justify-between md:gap-6">
        <Greeting name={name} />
        <PeopleStrip />
      </div>
      <ScopeBar needs={<NeedsChips />} />
      <div className="flex flex-col gap-2.5 md:grid md:h-[800px] md:grid-cols-[1.3fr_1fr_.8fr] md:grid-rows-[1fr_auto] md:gap-[18px] md:[grid-template-areas:'feed_chat_next''feed_chat_photos']">
        <UpNextTile open={open === "next"} onToggle={toggle} />
        <ChatsTile open={open === "chat"} onToggle={toggle} />
        <PhotosTile open={open === "photos"} onToggle={toggle} />
        <FeedTile open={open === "feed"} onToggle={toggle} />
      </div>
    </div>
  );
}
