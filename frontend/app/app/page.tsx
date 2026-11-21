"use client";
/**
 * @file app/app/page.tsx
 * @brief Home: glass bento (feed, chats, up next, photos) with scope + accordion.
 */
import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { homeStagger, homeTile } from "@/components/ui/motion";
import { useSession } from "@/stores/session";
import { useHomeChats } from "@/hooks/useHomeChats";
import { useHomeAccordion } from "@/hooks/useHomeAccordion";
import { Greeting } from "@/components/home/Greeting";
import { ScopeBar } from "@/components/home/ScopeBar";
import { PeopleStrip } from "@/components/home/PeopleStrip";
import { NeedsChips } from "@/components/home/NeedsChips";
import { PeopleTile } from "@/components/home/tiles/PeopleTile";
import { ListsTile } from "@/components/home/tiles/ListsTile";
import { FeedTile } from "@/components/home/tiles/FeedTile";
import { ChatsTile } from "@/components/home/tiles/ChatsTile";
import { UpNextTile } from "@/components/home/tiles/UpNextTile";
import { PhotosTile } from "@/components/home/tiles/PhotosTile";

/** Entrance plays once per session (module-level). */
let entrancePlayed = false;

/**
 * @brief Home page.
 * @return page element
 */
export default function AppHome() {
  const user = useSession((s) => s.user);
  const name = user?.display_name ?? user?.username ?? "there";
  const { data } = useHomeChats();
  const mention = (data?.items ?? []).some((t) => t.mentions_me);
  const reduced = useReducedMotion();
  // Captured on first render so a re-render mid-entrance keeps animating.
  const [animateIn] = React.useState(() => !entrancePlayed && !reduced);
  React.useEffect(() => {
    entrancePlayed = true;
  }, []);
  const rootProps = animateIn
    ? ({ variants: homeStagger, initial: "hidden", animate: "show" } as const)
    : {};
  const sectionProps = animateIn ? { variants: homeTile } : {};
  const { open, toggle } = useHomeAccordion(mention ? "chat" : "next");
  return (
    <motion.div className="py-6" {...rootProps}>
      <motion.div
        {...sectionProps}
        className="relative z-30 mb-4 flex flex-col gap-3.5 md:flex-row md:items-end md:justify-between md:gap-6"
      >
        <Greeting name={name} />
        <PeopleStrip />
      </motion.div>
      <motion.div {...sectionProps}>
        <ScopeBar needs={<NeedsChips />} />
      </motion.div>
      <motion.div
        {...sectionProps}
        className="flex flex-col gap-2.5 md:grid md:h-[1158px] md:grid-cols-[1.3fr_1fr_.8fr] md:grid-rows-[auto_1fr_340px] md:gap-[18px] md:[grid-template-areas:'feed_chat_next''feed_chat_photos''people_lists_lists'] min-[1800px]:h-[800px] min-[1800px]:grid-cols-[1.3fr_1fr_.8fr_.8fr] min-[1800px]:grid-rows-[auto_1fr] min-[1800px]:[grid-template-areas:'feed_chat_next_people''feed_chat_photos_lists']"
      >
        <UpNextTile open={open === "next"} onToggle={toggle} />
        <ChatsTile open={open === "chat"} onToggle={toggle} />
        <PhotosTile open={open === "photos"} onToggle={toggle} />
        <FeedTile open={open === "feed"} onToggle={toggle} />
        <PeopleTile open={open === "people"} onToggle={toggle} />
        <ListsTile open={open === "lists"} onToggle={toggle} />
      </motion.div>
    </motion.div>
  );
}
