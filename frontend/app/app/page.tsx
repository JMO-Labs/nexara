"use client";
/**
 * @file app/app/page.tsx
 * @brief Home hub page. Welcome banner + widget grid + gallery button.
 *        CalendarRail removed; upcoming events live in UpcomingEventsWidget.
 */
import "@/lib/widgets/builtins";
import { useHomeLayout } from "@/hooks/useHomeLayout";
import { useHomeSummary } from "@/hooks/useHomeSummary";
import { useSession } from "@/stores/session";
import { WelcomeBanner } from "@/components/home/WelcomeBanner";
import { WidgetGrid } from "@/components/home/WidgetGrid";
import { WidgetGallery } from "@/components/home/WidgetGallery";

export default function AppHome() {
  const user = useSession((s) => s.user);
  const layout = useHomeLayout();
  const summary = useHomeSummary();

  const userName = user?.display_name ?? user?.username ?? "there";
  const newPosts = summary.data?.new_posts ?? 0;
  const upcomingEvents = summary.data?.upcoming_events ?? 0;
  const unreadNotifications = summary.data?.unread_notifications ?? 0;

  return (
    <main className="flex flex-col gap-6 px-4 py-6 max-w-screen-2xl mx-auto w-full">
      <WelcomeBanner
        userName={userName}
        newPosts={newPosts}
        upcomingEvents={upcomingEvents}
        unreadNotifications={unreadNotifications}
        isLoading={summary.isLoading}
      />

      <WidgetGrid
        widgets={layout.widgets}
        onReorder={layout.reorder}
        onRemove={layout.removeWidget}
        onToggleCollapsed={layout.toggleCollapsed}
        onSizeChange={layout.setSize}
        isLoading={layout.isLoading}
      />

      <WidgetGallery
        presentDefIds={layout.widgets.map((w) => w.defId)}
        onAdd={(defId) => layout.addWidget(defId)}
        onReset={layout.resetToDefault}
      />
    </main>
  );
}
