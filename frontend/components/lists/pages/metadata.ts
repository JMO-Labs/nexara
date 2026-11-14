/**
 * @file components/lists/pages/metadata.ts
 * @brief SEO metadata builder shared by /app/lists routes.
 */
import type { Metadata } from "next";

/**
 * @brief Build page metadata with matching Open Graph fields.
 * @param title page title
 * @param description page description
 * @return Next.js Metadata
 */
export function listsMetadata(title: string, description: string): Metadata {
  return { title, description, openGraph: { title, description } };
}
