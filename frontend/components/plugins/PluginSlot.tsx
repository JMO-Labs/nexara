"use client";
/**
 * @file components/plugins/PluginSlot.tsx
 * @brief Renders all plugin components registered for a named slot, each in
 *        an error boundary and Suspense (spinner fallback).
 */
import { Component, Suspense, useSyncExternalStore } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { useToasts } from "@/stores/toasts";
import {
  PluginRegistry,
  type PluginManifest,
} from "@/lib/plugins/plugin-loader";

class PluginErrorBoundary extends Component<
  { pluginId: string; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`plugin "${this.props.pluginId}" crashed`, error, info);
    useToasts.getState().push({
      variant: "danger",
      message: `Plugin "${this.props.pluginId}" failed`,
    });
  }
  render() {
    if (this.state.failed)
      return (
        <div role="alert" className="text-sm text-destructive">
          Plugin &quot;{this.props.pluginId}&quot; failed to load.
        </div>
      );
    return this.props.children;
  }
}

function Spinner() {
  return (
    <div role="status" aria-label="Loading plugin" className="text-sm">
      <span className="sr-only">Loading…</span>
      <span aria-hidden>…</span>
    </div>
  );
}

/** @brief Named slot renderer. @param slotName e.g. "sidebar-widget". */
export function PluginSlot({ slotName }: { slotName: string }) {
  const registry = PluginRegistry.getInstance();
  useSyncExternalStore(
    registry.subscribe,
    registry.getVersion,
    registry.getVersion,
  );
  const entries = registry.getSlotComponents(slotName);
  if (entries.length === 0) return null;
  return (
    <div data-plugin-slot={slotName}>
      {entries.map(({ pluginId, component: C }, i) => {
        const manifest: PluginManifest = registry.getManifest(pluginId) ?? {
          id: pluginId,
          name: pluginId,
          version: "",
          is_enabled: true,
          description: "",
        };
        return (
          <PluginErrorBoundary key={`${pluginId}-${i}`} pluginId={pluginId}>
            <Suspense fallback={<Spinner />}>
              <C pluginId={pluginId} pluginManifest={manifest} />
            </Suspense>
          </PluginErrorBoundary>
        );
      })}
    </div>
  );
}
