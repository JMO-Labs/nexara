"use client";
/**
 * @file plugins/example-recipe-box/RecipeBoxWidget.tsx
 * @brief Example sidebar widget: a "Recipe Box" link.
 */
import type { PluginComponentProps } from "@/lib/plugins/plugin-loader";

export default function RecipeBoxWidget({ pluginId }: PluginComponentProps) {
  return (
    <a href={`/plugins/${pluginId}`} className="block px-3 py-2 text-sm">
      Recipe Box
    </a>
  );
}
