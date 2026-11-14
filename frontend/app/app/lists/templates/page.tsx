/**
 * @file app/app/lists/templates/page.tsx
 * @brief List templates route; renders TemplatesView.
 */
import type { Metadata } from "next";
import { TemplatesView } from "@/components/lists/pages/TemplatesView";
import { listsMetadata } from "@/components/lists/pages/metadata";

export async function generateMetadata(): Promise<Metadata> {
  return listsMetadata("List templates", "Browse and clone list templates.");
}

export default function Page() {
  return <TemplatesView />;
}
