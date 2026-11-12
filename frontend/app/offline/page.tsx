/**
 * @file app/offline/page.tsx
 * @brief Offline fallback served by the service worker when navigation
 *        fetches fail. Static so it can be precached at install.
 */
import Link from "next/link";
import { Button } from "@/components/ui";

export const dynamic = "force-static";

export const metadata = {
  title: "Offline",
};

export default function OfflinePage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-bg p-8 text-center text-ink">
      <h1 className="text-3xl font-black">You&rsquo;re offline</h1>
      <p className="max-w-[420px] text-sm opacity-80">
        Nexara can&rsquo;t reach the network right now. Check your connection
        and try again.
      </p>
      <Button asChild size="lg">
        <Link href="/app" prefetch={false}>
          Retry
        </Link>
      </Button>
    </main>
  );
}
