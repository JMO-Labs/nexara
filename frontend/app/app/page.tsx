"use client";
/**
 * @file app/app/page.tsx
 * @brief Home hub page. Welcome banner + widget grid.
 *        Customize drawer + chat drawer live in RightRail (mounted in Shell).
 */
import "@/lib/widgets/builtins";
import { useHomeLayout } from "@/hooks/useHomeLayout";
import { useHomeSummary } from "@/hooks/useHomeSummary";
import { useSession } from "@/stores/session";
import { WelcomeBanner } from "@/components/home/WelcomeBanner";
import { WidgetGrid } from "@/components/home/WidgetGrid";

export default function AppHome() {
  const user = useSession((s) => s.user);
  const layout = useHomeLayout();
  const summary = useHomeSummary();

  const userName = user?.display_name ?? user?.username ?? "there";
  const newPosts = summary.data?.new_posts ?? 0;
  const upcomingEvents = summary.data?.upcoming_events ?? 0;
  const unreadNotifications = summary.data?.unread_notifications ?? 0;

  return (
    <main className="flex flex-col gap-4 px-4 md:px-6 py-6 max-w-[1440px] mx-auto w-full">
      <WelcomeBanner
        userName={userName}
        newPosts={newPosts}
        upcomingEvents={upcomingEvents}
        unreadNotifications={unreadNotifications}
        isLoading={summary.isLoading}
      />

      <WidgetGrid
        widgets={layout.widgets}
        onApplyLayout={layout.applyLayout}
        onRemove={layout.removeWidget}
        onToggleCollapsed={layout.toggleCollapsed}
        isLoading={layout.isLoading}
      />
    </main>
  );
}
