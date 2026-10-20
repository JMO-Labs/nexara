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
    <main className="flex flex-col px-4 md:px-6 py-6 max-w-[1440px] mx-auto w-full">
      <WelcomeBanner
        userName={userName}
        newPosts={newPosts}
        upcomingEvents={upcomingEvents}
        unreadNotifications={unreadNotifications}
        isLoading={summary.isLoading}
      />

      {/* Editorial break — fading hairline with a terracotta diamond
          marker, framing the dashboard as the "section break" of the page. */}
      <div
        aria-hidden="true"
        style={{
          position: "relative",
          marginTop: 28,
          marginBottom: 16,
          height: 1,
          background:
            "linear-gradient(90deg, transparent 0%, var(--joy-palette-divider) 18%, var(--joy-palette-divider) 82%, transparent 100%)",
        }}
      >
        <span
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: 8,
            height: 8,
            transform: "translate(-50%, -50%) rotate(45deg)",
            background: "var(--joy-palette-primary-500)",
            boxShadow: "0 0 0 4px var(--joy-palette-background-body)",
          }}
        />
      </div>

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
