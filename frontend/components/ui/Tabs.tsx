/**
 * @file components/ui/Tabs.tsx
 * @brief Value-based Radix tabs with Garden Club styling.
 */
import * as React from "react";
import { Tabs as T } from "radix-ui";
import { cn } from "@/lib/utils";

export const Tabs = T.Root;

/**
 * @brief Tab strip.
 * @return tablist
 */
export function TabList({
  className,
  ...p
}: React.ComponentProps<typeof T.List>) {
  return (
    <T.List
      className={cn("inline-flex gap-1 rounded-full bg-bg p-1", className)}
      {...p}
    />
  );
}

/**
 * @brief Tab trigger; `value` selects its panel.
 * @return tab
 */
export function Tab({
  className,
  ...p
}: React.ComponentProps<typeof T.Trigger>) {
  return (
    <T.Trigger
      className={cn(
        "rounded-full px-4 py-1.5 text-sm font-semibold text-ink/70 transition-colors data-[state=active]:bg-accent data-[state=active]:text-surface-strong disabled:opacity-50",
        className,
      )}
      {...p}
    />
  );
}

/**
 * @brief Panel for a tab `value`.
 * @return tabpanel
 */
export function TabPanel({
  className,
  ...p
}: React.ComponentProps<typeof T.Content>) {
  return <T.Content className={cn("mt-3", className)} {...p} />;
}
