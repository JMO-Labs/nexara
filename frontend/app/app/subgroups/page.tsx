/**
 * @file app/app/subgroups/page.tsx
 * @brief Legacy Groups index; redirects to /app/community?view=groups.
 */
import { redirect } from "next/navigation";

type SearchParams = Record<string, string | string[] | undefined>;

/**
 * @brief Redirect to the Community groups view, preserving the query string.
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
  qs.set("view", "groups");
  redirect(`/app/community?${qs}`);
}
