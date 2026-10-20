"use client";
/**
 * @file components/home/widgets/QuickActionsWidget.tsx
 * @brief Buttons that open the create post / event / gallery modals.
 */
import * as React from "react";
import { CalendarPlus, ImagePlus, PenSquare } from "lucide-react";
import { Button } from "@/components/ui";
import { useModals } from "@/stores/modals";

/**
 * @brief Quick actions widget body.
 * @return three action buttons
 */
export function QuickActionsWidget() {
  const show = useModals((s) => s.show);
  return (
    <div className="flex flex-col gap-2">
      <Button
        variant="outline"
        size="sm"
        aria-label="New post"
        onClick={() => show("create-post")}
      >
        <PenSquare aria-hidden className="size-4" />
        New post
      </Button>
      <Button
        variant="outline"
        size="sm"
        aria-label="Create event"
        onClick={() => show("create-event")}
      >
        <CalendarPlus aria-hidden className="size-4" />
        Create event
      </Button>
      <Button
        variant="outline"
        size="sm"
        aria-label="Upload media"
        onClick={() => show("create-gallery")}
      >
        <ImagePlus aria-hidden className="size-4" />
        Upload media
      </Button>
    </div>
  );
}

export default QuickActionsWidget;
