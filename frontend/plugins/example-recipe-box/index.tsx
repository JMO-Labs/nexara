/**
 * @file plugins/example-recipe-box/index.tsx
 * @brief Example plugin entry point; lazy-registers RecipeBoxWidget.
 */
import { lazy } from "react";
import type { PluginRegistry } from "@/lib/plugins/plugin-loader";

export const RecipeBoxWidget = lazy(
  () => import("./components/RecipeBoxWidget"),
);

/** @brief Register this plugin's slot components. */
export function registerPlugin(registry: PluginRegistry): void {
  registry.registerSlotComponent(
    "sidebar-widget",
    "example-recipe-box",
    RecipeBoxWidget,
  );
}
