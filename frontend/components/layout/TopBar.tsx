"use client";
/**
 * @file components/layout/TopBar.tsx
 * @brief Sticky top bar. Desktop: lockup, pill nav, create, search, bell,
 *        avatar. Phone: lockup, create, bell, avatar button (More sheet).
 */
import { useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";
import { Avatar } from "@/components/ui/Avatar";
import { BrandLockup } from "@/components/brand/Logo";
import { NotificationsBell } from "@/components/notifications/NotificationsBell";
import { AvatarMenu } from "./AvatarMenu";
import { TopNav } from "./TopNav";
import { CreateMenu } from "./CreateMenu";
import { MoreSheet } from "./MoreSheet";
import { useUI } from "@/stores/ui";
import { useSession } from "@/stores/session";
import { useBrandingStore } from "@/stores/branding";

/**
 * @brief Top bar.
 * @return header element
 */
export function TopBar() {
  const openPalette = useUI((s) => s.setCommandPaletteOpen);
  const { name, logoUrl } = useBrandingStore();
  const user = useSession((s) => s.user);
  const [moreOpen, setMoreOpen] = useState(false);
  return (
    <header className="sticky top-0 z-20 flex items-center gap-2 px-4 py-2 md:px-8">
      <Link
        href="/app"
        aria-label={`${name} home`}
        className="focus-visible:outline-accent rounded-xl focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        <BrandLockup logoUrl={logoUrl} name={name} size={32} />
      </Link>
      <div className="hidden flex-1 justify-center md:flex">
        <TopNav />
      </div>
      <div className="ml-auto flex items-center gap-2 md:ml-0">
        <CreateMenu className="hidden md:inline-flex" />
        <CreateMenu compact className="md:hidden" />
        <IconButton
          variant="ghost"
          className="glass-btn size-10 md:size-11"
          aria-label="Search"
          tooltip="Search"
          tooltipSide="bottom"
          shortcut="Ctrl+K"
          data-tour="topbar-search"
          onClick={() => openPalette(true)}
        >
          <Search aria-hidden className="size-5" />
        </IconButton>
        <NotificationsBell />
        <div className="hidden md:block">
          <AvatarMenu />
        </div>
        <button
          type="button"
          aria-label="More"
          aria-haspopup="dialog"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen(true)}
          className="focus-visible:outline-accent rounded-full p-1 focus-visible:outline-2 focus-visible:outline-offset-2 md:hidden"
        >
          <Avatar
            src={user?.avatar_url ?? undefined}
            name={user?.display_name ?? "You"}
            size="md"
          />
        </button>
      </div>
      <MoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} />
    </header>
  );
}
