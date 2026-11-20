/**
 * @file app/app/bookmarks/page.tsx
 * @brief Legacy bookmarks route; redirects to /app/inbox?view=saved.
 */
import { redirect } from "next/navigation";

type SearchParams = Record<string, string | string[] | undefined>;

/**
 * @brief Redirect to the Inbox Saved tab, preserving other query params.
 * @param props searchParams promise
 * @return never
 */
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) {
    if (Array.isArray(v)) v.forEach((x) => qs.append(k, x));
    else if (v !== undefined) qs.append(k, v);
  }
  qs.set("view", "saved");
  redirect(`/app/inbox?${qs}`);
}
