"use client";
/**
 * @file components/ui/Drawer.tsx
 * @brief Side/bottom drawer built on shadcn sheet (Radix dialog).
 */
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "./sheet";

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  side?: "left" | "right" | "bottom";
  children: ReactNode;
}

/**
 * @brief Accessible drawer.
 * @param props see DrawerProps
 * @return sheet element
 */
export function Drawer({
  open,
  onClose,
  title,
  side = "right",
  children,
}: DrawerProps) {
  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side={side}
        aria-describedby={undefined}
        className={cn(
          "bg-surface text-ink",
          side === "bottom" &&
            "max-h-[85dvh] overflow-y-auto rounded-t-[1.25rem] pb-[env(safe-area-inset-bottom)]",
        )}
      >
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
        </SheetHeader>
        <div className="px-4 pb-4">{children}</div>
      </SheetContent>
    </Sheet>
  );
}

export default Drawer;
