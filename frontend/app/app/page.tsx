"use client";
/**
 * @file app/app/page.tsx
 * @brief Home: greeting, next-up card, live feed, desktop widget column.
 */
import { useSession } from "@/stores/session";
import { WelcomeBanner } from "@/components/home/WelcomeBanner";
import { NextUpCard } from "@/components/home/NextUpCard";
import { HomeFeed } from "@/components/home/HomeFeed";
import { WidgetColumn } from "@/components/home/WidgetColumn";

/**
 * @brief Home page.
 * @return page element
 */
export default function AppHome() {
  const user = useSession((s) => s.user);
  const name = user?.display_name ?? user?.username ?? "there";
  return (
    <main className="px-4 md:px-6 py-6 max-w-[1100px] mx-auto w-full">
      <WelcomeBanner userName={name} />
      <div className="md:flex md:gap-6 md:items-start">
        <div className="min-w-0 w-full md:max-w-2xl">
          <NextUpCard />
          <HomeFeed />
        </div>
        <WidgetColumn />
      </div>
    </main>
  );
}
