"use client";
/**
 * @file components/ui/Drawer.tsx
 * @brief Side/bottom drawer built on shadcn sheet (Radix dialog).
 */
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "./shadcn/sheet";

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
          side === "right"
            ? "glass z-[1100] inset-y-3 right-3 h-auto max-h-[calc(100dvh-1.5rem)] rounded-[32px] border-0 bg-[var(--nx-glass)] text-ink"
            : "z-[1100] bg-[var(--nx-glass-solid)] text-ink border-[var(--nx-glass-edge)]",
          side === "bottom" &&
            "max-h-[85dvh] overflow-y-auto rounded-t-[28px] pb-[env(safe-area-inset-bottom)]",
        )}
      >
        <SheetHeader>
          <SheetTitle className="text-xl font-medium">{title}</SheetTitle>
        </SheetHeader>
        <div className="px-4 pb-4">{children}</div>
      </SheetContent>
    </Sheet>
  );
}

export default Drawer;
