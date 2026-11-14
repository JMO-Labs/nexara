/**
 * @file app/app/lists/[id]/page.tsx
 * @brief List route; renders ListDetailView.
 */
import type { Metadata } from "next";
import { ListDetailView } from "@/components/lists/pages/ListDetailView";
import { listsMetadata } from "@/components/lists/pages/metadata";

export async function generateMetadata(): Promise<Metadata> {
  return listsMetadata("List", "View list items, members and settings.");
}

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ListDetailView id={id} />;
}
