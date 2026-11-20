/**
 * @file app/app/kudos/page.tsx
 * @brief Legacy Kudos route; redirects to the Home feed Kudos filter.
 */
import { redirect } from "next/navigation";

/**
 * @brief Redirect to /app with the Kudos feed filter selected.
 * @return never
 */
export default function KudosPage() {
  redirect("/app?feed=kudos");
}
