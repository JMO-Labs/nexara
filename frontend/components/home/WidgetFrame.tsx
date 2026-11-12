/**
 * @file components/home/WidgetFrame.tsx
 * @brief Titled card around a home widget; optional header actions.
 */
import * as React from "react";
import { Card } from "@/components/ui";

export interface WidgetFrameProps {
  title: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

/**
 * @brief Simple titled card (no collapse).
 * @param title heading text
 * @param actions optional header controls (e.g. drag handle)
 * @return card element
 */
export function WidgetFrame({ title, actions, children }: WidgetFrameProps) {
  return (
    <Card className="p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-ink truncate">{title}</h2>
        {actions}
      </div>
      {children}
    </Card>
  );
}

export default WidgetFrame;
