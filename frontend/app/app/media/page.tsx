/**
 * @file app/app/media/page.tsx
 * @brief Legacy media route; redirects to the All photos view.
 */
import { redirect } from "next/navigation";

/**
 * @brief Redirect to /app/photos?view=all.
 * @return never
 */
export default function Page() {
  redirect("/app/photos?view=all");
}
