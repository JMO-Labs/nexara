"use client";
/**
 * @file components/settings/StorageTab.tsx
 * @brief Storage settings tab (placeholder).
 */
import { Card, EmptyState } from "@/components/ui";

/**
 * @brief Storage placeholder.
 * @return storage tab content
 */
export function StorageTab() {
  return (
    <Card className="max-w-3xl p-4 md:p-6">
      <h2 className="mb-2 text-lg font-semibold">Storage</h2>
      <EmptyState
        title="Storage usage coming soon"
        description="Storage usage analytics will be available in a future update."
      />
    </Card>
  );
}
