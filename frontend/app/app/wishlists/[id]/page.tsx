/**
 * @file app/app/wishlists/[id]/page.tsx
 * @brief Wishlist detail route.
 */
"use client";

import { use } from "react";
import { WishlistPage } from "@/components/wishlists/WishlistPage";

export default function WishlistRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <WishlistPage id={id} />;
}
