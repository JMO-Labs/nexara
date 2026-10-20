/**
 * @file app/page.tsx
 * @brief Public landing. Signed-in users (session hint cookie) go to /app;
 *        everyone else sees a minimal welcome with a sign-in link.
 */
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui";

/**
 * @brief Landing page server component.
 * @return welcome screen, or a redirect to /app
 */
export default async function Home() {
  if ((await cookies()).has("nx_session")) redirect("/app");
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-bg px-4 py-8 text-center text-ink">
      <p className="text-3xl font-black">Nexara</p>
      <h1 className="text-2xl font-semibold">Welcome to the Garden Club</h1>
      <p className="max-w-sm text-sm opacity-80">
        A private home for your family and friends.
      </p>
      <Button asChild size="lg">
        <Link href="/login">Sign in</Link>
      </Button>
    </main>
  );
}
