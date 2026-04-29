"use client";
/**
 * @file components/home/widgets/QuickActionsWidget.tsx
 * @brief Static quick-action buttons: New post, Create event, Upload media.
 *        Opens existing modal flows via the modal store.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import {
  PencilSquareIcon,
  CalendarDaysIcon,
  PhotoIcon,
} from "@heroicons/react/24/outline";
import { useModals } from "@/stores/modals";
import type { WidgetContext } from "@/lib/widgets/registry";

interface ActionButtonProps {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
}

function ActionButton({ label, icon, onClick }: ActionButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="flex flex-col items-center gap-2 p-3 rounded-xl border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)] flex-1 min-w-0"
    >
      <div className="w-9 h-9 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
        {icon}
      </div>
      <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300 text-center leading-tight">
        {label}
      </span>
    </button>
  );
}

export function QuickActionsWidget(_: WidgetContext) {
  const show = useModals((s) => s.show);

  return (
    <Stack direction="row" spacing={1.5} sx={{ flexWrap: "nowrap" }}>
      <ActionButton
        label="New post"
        icon={<PencilSquareIcon aria-hidden width={20} height={20} />}
        onClick={() => show("create-post")}
      />
      <ActionButton
        label="Create event"
        icon={<CalendarDaysIcon aria-hidden width={20} height={20} />}
        onClick={() => show("create-event")}
      />
      <ActionButton
        label="Upload media"
        icon={<PhotoIcon aria-hidden width={20} height={20} />}
        onClick={() => show("create-gallery")}
      />
    </Stack>
  );
}

export default QuickActionsWidget;
