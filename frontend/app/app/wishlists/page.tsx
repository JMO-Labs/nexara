/**
 * @file app/app/wishlists/page.tsx
 * @brief Wishlists: yours (and your household's), then everyone else's you can see.
 */
"use client";

import { PageHeader } from "@/components/ui/page";
import { WishlistCards } from "@/components/wishlists/WishlistCards";
import { useSession } from "@/stores/session";

export default function WishlistsRoute() {
  const me = useSession((s) => s.user?.id);
  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-6 pb-8">
      <PageHeader
        title="Wishlists"
        description="Gift ideas for birthdays, holidays and more. People never see who is getting them what."
      />
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">
          Yours and your household&apos;s
        </h2>
        {me && <WishlistCards query={{ person_id: me }} canCreate />}
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Family and friends</h2>
        <WishlistCards
          othersOnly
          emptyText="No one has shared a wishlist with you yet"
        />
      </section>
    </div>
  );
}
