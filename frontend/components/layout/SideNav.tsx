"use client";
/**
 * @file components/layout/SideNav.tsx
 * @brief Desktop icon rail (64px) that expands to 220px on hover or focus.
 */
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSession } from "@/stores/session";
import {
  MORE_NAV,
  PRIMARY_NAV,
  isNavActive,
  visibleNav,
  type NavItem,
} from "./navItems";

function NavLink({
  item,
  active,
  open,
}: {
  item: NavItem;
  active: boolean;
  open: boolean;
}) {
  const { Icon } = item;
  return (
    <li>
      <Link
        href={item.href}
        aria-current={active ? "page" : undefined}
        className={cn(
          "flex h-10 items-center gap-3 rounded-2xl px-3 text-sm font-semibold",
          active
            ? "bg-accent text-surface-strong"
            : "text-muted hover:bg-white/10",
        )}
      >
        <Icon aria-hidden className="size-5 shrink-0" />
        <span className={open ? "" : "sr-only"}>{item.label}</span>
      </Link>
    </li>
  );
}

/**
 * @brief Desktop side navigation.
 * @return nav element, hidden below md
 */
export function SideNav() {
  const pathname = usePathname();
  const user = useSession((s) => s.user);
  const isAdmin = !!(user?.is_admin ?? user?.role === "admin");
  const [open, setOpen] = useState(false);

  const render = (items: NavItem[]) =>
    visibleNav(items, isAdmin).map((i) => (
      <NavLink
        key={i.href}
        item={i}
        active={isNavActive(pathname, i.href)}
        open={open}
      />
    ));

  return (
    <nav
      aria-label="Main"
      data-expanded={open ? "true" : "false"}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocusCapture={() => setOpen(true)}
      onBlurCapture={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null))
          setOpen(false);
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          setOpen(false);
          (document.activeElement as HTMLElement | null)?.blur();
        }
      }}
      className={cn(
        "fixed inset-y-0 left-0 z-30 hidden flex-col gap-2 overflow-hidden bg-surface-strong p-2 md:flex",
        "motion-safe:transition-[width] motion-safe:duration-200",
        open ? "w-[220px]" : "w-16",
      )}
    >
      <div className="flex h-10 items-center gap-3 px-1">
        <span
          aria-hidden
          className="grid size-10 shrink-0 place-items-center rounded-2xl bg-sun font-black text-surface-strong"
        >
          N
        </span>
      </div>
      <ul className="flex flex-col gap-1">{render(PRIMARY_NAV)}</ul>
      <hr className="border-white/10" />
      <ul className="flex flex-col gap-1">{render(MORE_NAV)}</ul>
    </nav>
  );
}
