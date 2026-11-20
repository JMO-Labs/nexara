"use client";
/**
 * @file components/admin/InterestsTab.tsx
 * @brief Interest analytics display with chip-style categories.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getInterestAnalytics } from "@/lib/api/interests";
import { Chip, EmptyState } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { Hash } from "lucide-react";
import { AdminLoading, AdminNotice } from "./AdminState";

/**
 * @brief Capitalise the first letter of a category slug.
 * @param s slug, e.g. "music"
 * @return label, e.g. "Music"
 */
const capitalise = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/**
 * @brief Interests admin tab body.
 * @return tab content
 */
export function InterestsTab() {
  const {
    data: analytics,
    isLoading,
    error,
  } = useQuery({
    queryKey: qk.admin.interestsAnalytics(),
    queryFn: getInterestAnalytics,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) return <AdminLoading />;

  if (error) {
    return (
      <AdminNotice tone="error">Failed to load interest analytics</AdminNotice>
    );
  }

  if (!analytics || analytics.length === 0) {
    return (
      <Panel as="div">
        <EmptyState
          compact
          icon={Hash}
          title="No interest data yet"
          description="Interest activity will appear here once members pick interests."
        />
      </Panel>
    );
  }

  // Group by category
  const grouped = analytics.reduce(
    (acc, item) => {
      if (!acc[item.category_slug]) acc[item.category_slug] = [];
      acc[item.category_slug].push(item);
      return acc;
    },
    {} as Record<string, typeof analytics>,
  );

  return (
    <div className="flex flex-col gap-4">
      {Object.entries(grouped).map(([category, items]) => (
        <Panel key={category} as="div" title={capitalise(category)}>
          <div className="flex flex-wrap gap-2">
            {items
              .sort((a, b) => b.count - a.count)
              .map((item, idx) => (
                <Chip key={`${item.value}-${idx}`}>
                  {item.value}
                  <span className="ml-1 opacity-70">{item.count}</span>
                </Chip>
              ))}
          </div>
        </Panel>
      ))}
    </div>
  );
}
