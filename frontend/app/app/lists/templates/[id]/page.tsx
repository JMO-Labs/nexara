/**
 * @file app/app/lists/templates/[id]/page.tsx
 * @brief Edit template route; renders TemplateEditView.
 */
import type { Metadata } from "next";
import { TemplateEditView } from "@/components/lists/pages/TemplateDesignerView";
import { listsMetadata } from "@/components/lists/pages/metadata";

export async function generateMetadata(): Promise<Metadata> {
  return listsMetadata("Edit template", "Edit a list template's fields.");
}

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <TemplateEditView id={id} />;
}
