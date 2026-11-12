"use client";
/**
 * @file components/admin/InterestsTab.tsx
 * @brief Interest analytics display with chip-style categories.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getInterestAnalytics } from "@/lib/api/interests";
import { Card, Chip } from "@/components/ui";
import { AdminLoading, AdminNotice } from "./AdminState";

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
    return <AdminNotice>No interest data available yet</AdminNotice>;
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
        <Card key={category} className="p-4">
          <h3 className="mb-2 text-sm font-semibold capitalize">{category}</h3>
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
        </Card>
      ))}
    </div>
  );
}
