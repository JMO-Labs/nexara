/**
 * @file app/app/galleries/page.tsx
 * @brief Legacy galleries route; redirects to /app/photos keeping the query.
 */
import { redirect } from "next/navigation";

type SearchParams = Record<string, string | string[] | undefined>;

/**
 * @brief Redirect to the Photos page, preserving the query string.
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
  const s = qs.toString();
  redirect(s ? `/app/photos?${s}` : "/app/photos");
}
