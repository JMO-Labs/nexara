/**
 * @file app/app/lists/new/page.tsx
 * @brief New list route; renders ListNewView.
 */
import type { Metadata } from "next";
import { ListNewView } from "@/components/lists/pages/ListNewView";
import { listsMetadata } from "@/components/lists/pages/metadata";

export async function generateMetadata(): Promise<Metadata> {
  return listsMetadata(
    "New list",
    "Create a new list from scratch or a template.",
  );
}

export default function Page() {
  return <ListNewView />;
}
