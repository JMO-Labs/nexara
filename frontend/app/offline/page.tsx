/**
 * @file app/offline/page.tsx
 * @brief Offline fallback served by the service worker when navigation
 *        fetches fail. Static so it can be precached at install: no client
 *        hooks, CSS tokens only.
 */
import Link from "next/link";
import { WifiOff } from "lucide-react";
import { Button } from "@/components/ui";
import { BrandLockup } from "@/components/brand/Logo";

export const dynamic = "force-static";

export const metadata = {
  title: "Offline",
};

export default function OfflinePage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg p-4 text-ink">
      <div className="glass flex w-full max-w-md flex-col items-center gap-4 rounded-[32px] p-8 text-center">
        <BrandLockup name="Nexara" size={32} />
        <span className="glass-item grid size-16 place-items-center rounded-full">
          <WifiOff className="size-7" aria-hidden="true" />
        </span>
        <h1 className="text-2xl font-medium tracking-tight">
          You&rsquo;re offline
        </h1>
        <p className="max-w-[420px] text-sm text-muted">
          Nexara can&rsquo;t reach the network right now. Check your connection
          and try again.
        </p>
        <Button asChild size="lg">
          <Link href="/app" prefetch={false}>
            Retry
          </Link>
        </Button>
      </div>
    </main>
  );
}
