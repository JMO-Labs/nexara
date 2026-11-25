"use client";
/**
 * @file components/layout/CreateMenu.tsx
 * @brief "Create" dropdown: new post / event / photos / list / trip.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import {
  CalendarPlus,
  Hourglass,
  ImagePlus,
  Gift,
  ListPlus,
  PenSquare,
  Plus,
  Route,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useFeature } from "@/hooks/useFeature";
import { StartTripDialog } from "@/components/trips/StartTripDialog";
import { useModals } from "@/stores/modals";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/shadcn/dropdown-menu";

/**
 * @brief Create menu.
 * @param compact icon-only trigger
 * @return dropdown menu
 */
export function CreateMenu({
  compact,
  className,
}: {
  compact?: boolean;
  className?: string;
}) {
  const router = useRouter();
  const show = useModals((s) => s.show);
  const trips = useFeature("safe_arrival");
  const [tripOpen, setTripOpen] = React.useState(false);
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="Create"
          className={cn(
            "bg-ink text-bg focus-visible:outline-accent inline-flex h-11 items-center justify-center gap-2 rounded-full font-medium focus-visible:outline-2 focus-visible:outline-offset-2",
            compact ? "size-11" : "px-5",
            className,
          )}
        >
          <Plus aria-hidden className="size-5" />
          {!compact && <span>Create</span>}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-48">
          <DropdownMenuItem onSelect={() => show("create-post")}>
            <PenSquare aria-hidden className="size-4" />
            New post
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => show("create-event")}>
            <CalendarPlus aria-hidden className="size-4" />
            New event
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => show("create-gallery")}>
            <ImagePlus aria-hidden className="size-4" />
            Upload photos
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => router.push("/app/lists/new")}>
            <ListPlus aria-hidden className="size-4" />
            New list
          </DropdownMenuItem>
          <DropdownMenuItem
            onSelect={() => router.push("/app/lists/new?type=wishlist")}
          >
            <Gift aria-hidden className="size-4" />
            New wishlist
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => show("create-countdown")}>
            <Hourglass aria-hidden className="size-4" />
            Countdown
          </DropdownMenuItem>
          {trips && (
            <DropdownMenuItem onSelect={() => setTripOpen(true)}>
              <Route aria-hidden className="size-4" />
              Start a trip
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      {trips && tripOpen && (
        <StartTripDialog open={tripOpen} onClose={() => setTripOpen(false)} />
      )}
    </>
  );
}
