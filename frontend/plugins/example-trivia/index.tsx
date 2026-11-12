/**
 * @file plugins/example-trivia/index.tsx
 * @brief Example trivia plugin entry point; lazy-registers TriviaWidget in
 *        the "sidebar-widget" slot. PluginSlot wraps each slot component in
 *        Suspense with a spinner fallback.
 */
import { lazy } from "react";
import type { PluginRegistry } from "@/lib/plugins/plugin-loader";

export const PLUGIN_ID = "example-trivia";

export const TriviaWidget = lazy(() => import("./components/TriviaWidget"));

/** @brief Register this plugin's slot components. */
export function registerPlugin(registry: PluginRegistry): void {
  registry.registerSlotComponent("sidebar-widget", PLUGIN_ID, TriviaWidget);
}

export default registerPlugin;
