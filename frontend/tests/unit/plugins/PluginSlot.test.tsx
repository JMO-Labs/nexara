/**
 * @file PluginSlot.test.tsx
 * @brief Tests for PluginSlot rendering, error boundary and lazy loading.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { lazy } from "react";

vi.mock("@/lib/api/client", () => ({ apiGet: vi.fn() }));
import { PluginRegistry } from "@/lib/plugins/plugin-loader";
import { PluginSlot } from "@/components/plugins/PluginSlot";

const reg = () => PluginRegistry.getInstance();

describe("PluginSlot", () => {
  beforeEach(() => reg().reset());

  it("renders registered components with plugin props", () => {
    reg().registerSlotComponent("sidebar-widget", "a", ({ pluginId }: { pluginId: string }) => (
      <div>widget-{pluginId}</div>
    ));
    render(<PluginSlot slotName="sidebar-widget" />);
    expect(screen.getByText("widget-a")).toBeInTheDocument();
  });

  it("renders nothing for an empty slot", () => {
    const { container } = render(<PluginSlot slotName="admin-tab" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("catches crashes without breaking siblings", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    reg().registerSlotComponent("sidebar-widget", "bad", () => {
      throw new Error("boom");
    });
    reg().registerSlotComponent("sidebar-widget", "good", () => <div>fine</div>);
    render(<PluginSlot slotName="sidebar-widget" />);
    expect(screen.getByRole("alert")).toHaveTextContent(/bad/);
    expect(screen.getByText("fine")).toBeInTheDocument();
  });

  it("shows spinner fallback then lazy component", async () => {
    const Lazy = lazy(async () => ({ default: () => <div>lazy-done</div> }));
    reg().registerSlotComponent("sidebar-widget", "l", Lazy);
    render(<PluginSlot slotName="sidebar-widget" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(await screen.findByText("lazy-done")).toBeInTheDocument();
  });

  it("re-renders when a component registers later", () => {
    render(<PluginSlot slotName="post-action" />);
    act(() => reg().registerSlotComponent("post-action", "x", () => <div>late</div>));
    expect(screen.getByText("late")).toBeInTheDocument();
  });
});
