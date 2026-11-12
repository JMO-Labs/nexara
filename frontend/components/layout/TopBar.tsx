"use client";
/**
 * @file components/layout/TopBar.tsx
 * @brief Sticky top bar. Phone: logo mark, search, bell. Desktop: search,
 *        bell, avatar menu (side nav carries the logo).
 */
import Link from "next/link";
import { Search } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";
import { NotificationsBell } from "@/components/notifications/NotificationsBell";
import { AvatarMenu } from "./AvatarMenu";
import { useUI } from "@/stores/ui";
import { useBrandingStore } from "@/stores/branding";

/**
 * @brief Top bar.
 * @return header element
 */
export function TopBar() {
  const openPalette = useUI((s) => s.setCommandPaletteOpen);
  const { name, logoUrl } = useBrandingStore();
  return (
    <header className="bg-bg sticky top-0 z-20 flex items-center gap-2 px-4 py-2 md:px-8">
      <Link
        href="/app"
        aria-label={`${name} home`}
        className="bg-sun text-surface-strong focus-visible:outline-accent grid size-9 place-items-center rounded-xl font-black focus-visible:outline-2 focus-visible:outline-offset-2 md:hidden"
      >
        {logoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={logoUrl}
            alt=""
            className="size-9 rounded-xl object-cover"
          />
        ) : (
          name.charAt(0).toUpperCase()
        )}
      </Link>
      <div className="ml-auto flex items-center gap-1">
        <IconButton
          variant="ghost"
          aria-label="Search"
          tooltip="Search"
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
      </div>
    </header>
  );
}
