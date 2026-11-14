/**
 * @file app/app/lists/[id]/edit/page.tsx
 * @brief Edit list route; renders ListEditView.
 */
import type { Metadata } from "next";
import { ListEditView } from "@/components/lists/pages/ListDetailView";
import { listsMetadata } from "@/components/lists/pages/metadata";

export async function generateMetadata(): Promise<Metadata> {
  return listsMetadata(
    "Edit list",
    "Edit a list's title, description and expiry.",
  );
}

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ListEditView id={id} />;
}
