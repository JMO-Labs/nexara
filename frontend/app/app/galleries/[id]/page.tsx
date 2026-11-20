/**
 * @file app/app/galleries/[id]/page.tsx
 * @brief Legacy gallery detail route; redirects to the Photos album drawer.
 */
import { redirect } from "next/navigation";

/**
 * @brief Redirect to /app/photos?gallery=<id>.
 * @param props params promise
 * @return never
 */
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/app/photos?${new URLSearchParams({ gallery: id })}`);
}
