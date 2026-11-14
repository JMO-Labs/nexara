/**
 * @file app/app/lists/page.tsx
 * @brief Lists route; renders ListsBrowseView.
 */
import type { Metadata } from "next";
import { ListsBrowseView } from "@/components/lists/pages/ListsBrowseView";
import { listsMetadata } from "@/components/lists/pages/metadata";

export async function generateMetadata(): Promise<Metadata> {
  return listsMetadata("Lists", "Shared lists for your community.");
}

export default function Page() {
  return <ListsBrowseView />;
}
