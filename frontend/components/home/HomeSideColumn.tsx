"use client";
/**
 * @file components/home/HomeSideColumn.tsx
 * @brief People + Lists side column (lg+) that collapses sideways to an icon
 *        rail so the feed keeps the width. Below lg the wrappers are
 *        `display: contents`, so the tiles sit in the parent grid/accordion.
 *        No saved choice = auto: rail below 3xl, open at 3xl.
 */
import * as React from "react";
import { ChevronRight, ListChecks, PanelRightOpen, Users } from "lucide-react";
import { PeopleTile } from "@/components/home/tiles/PeopleTile";
import { ListsTile } from "@/components/home/tiles/ListsTile";
import type { TileSlotProps } from "@/components/home/HomeTile";
import { useHomePeople } from "@/hooks/useHomePeople";
import { cn } from "@/lib/utils";

type Mode = "auto" | "open" | "closed";
const KEY = "nx-home-side";

const read = (): Mode => {
  try {
    const v = localStorage.getItem(KEY);
    return v === "open" || v === "closed" ? v : "auto";
  } catch {
    return "auto";
  }
};

const subscribe = (cb: () => void) => {
  window.addEventListener(KEY, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(KEY, cb);
    window.removeEventListener("storage", cb);
  };
};

/**
 * @brief Side column.
 * @param open accordion id currently open (phone)
 * @param onToggle accordion toggle (phone)
 * @return column element
 */
export function HomeSideColumn({
  open,
  onToggle,
}: {
  open: string | null;
  onToggle: TileSlotProps["onToggle"];
}) {
  const mode = React.useSyncExternalStore(subscribe, read, () => "auto");
  const set = (m: Mode) => {
    try {
      localStorage.setItem(KEY, m);
    } catch {
      /* private mode: choice is not kept */
    }
    window.dispatchEvent(new Event(KEY));
  };
  const bdays =
    useHomePeople().data?.items.filter((p) => p.birthday_in_days != null)
      .length ?? 0;

  const tiles =
    mode === "open"
      ? "lg:flex"
      : mode === "closed"
        ? "lg:hidden"
        : "lg:hidden 3xl:flex";
  const rail =
    mode === "open"
      ? "lg:hidden"
      : mode === "closed"
        ? "lg:flex"
        : "lg:flex 3xl:hidden";

  const railBtn =
    "relative grid size-10 place-items-center rounded-full text-ink outline-none hover:bg-[color-mix(in_srgb,var(--nx-ink)_8%,transparent)] focus-visible:outline-2 focus-visible:outline-accent";

  return (
    <div className="contents lg:relative lg:flex lg:min-h-0 lg:[grid-area:side]">
      <div
        className={cn(
          "contents lg:min-h-0 lg:w-[300px] lg:flex-col lg:gap-[18px] 3xl:w-[340px]",
          tiles,
        )}
      >
        <PeopleTile open={open === "people"} onToggle={onToggle} />
        <ListsTile open={open === "lists"} onToggle={onToggle} />
        <button
          type="button"
          aria-label="Collapse side column"
          title="Collapse"
          onClick={() => set("closed")}
          className="glass absolute top-1/2 -left-[14px] z-10 hidden h-14 w-[10px] -translate-y-1/2 place-items-center rounded-full text-muted transition-[width] hover:w-4 hover:text-ink focus-visible:w-4 lg:grid"
        >
          <ChevronRight className="size-3" aria-hidden />
        </button>
      </div>
      <nav
        aria-label="Side column"
        className={cn(
          "glass hidden w-16 flex-col items-center gap-2 rounded-[28px] py-3",
          rail,
        )}
      >
        <button
          type="button"
          aria-label="Expand side column"
          title="Expand"
          onClick={() => set("open")}
          className={railBtn}
        >
          <PanelRightOpen className="size-4" aria-hidden />
        </button>
        <span className="h-px w-8 bg-[var(--nx-line)]" aria-hidden />
        <button
          type="button"
          aria-label={
            bdays
              ? `People, ${bdays} birthday${bdays === 1 ? "" : "s"} soon`
              : "People"
          }
          title="People"
          onClick={() => set("open")}
          className={railBtn}
        >
          <Users className="size-5" aria-hidden />
          {bdays > 0 && (
            <span className="absolute -top-0.5 -right-0.5 grid size-4 place-items-center rounded-full bg-[var(--nx-red)] text-[10px] font-semibold text-white">
              {bdays}
            </span>
          )}
        </button>
        <button
          type="button"
          aria-label="Lists"
          title="Lists"
          onClick={() => set("open")}
          className={railBtn}
        >
          <ListChecks className="size-5" aria-hidden />
        </button>
      </nav>
    </div>
  );
}
