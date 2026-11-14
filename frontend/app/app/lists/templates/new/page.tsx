/**
 * @file app/app/lists/templates/new/page.tsx
 * @brief New template route; renders TemplateNewView.
 */
import type { Metadata } from "next";
import { TemplateNewView } from "@/components/lists/pages/TemplateDesignerView";
import { listsMetadata } from "@/components/lists/pages/metadata";

export async function generateMetadata(): Promise<Metadata> {
  return listsMetadata("New template", "Design a new list template.");
}

export default function Page() {
  return <TemplateNewView />;
}
