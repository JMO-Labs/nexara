/**
 * @file tests/unit/settings/PushDevices.test.tsx
 * @brief PushDevices: this-device marker, rename, remove, enable, iOS hint.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const api = vi.hoisted(() => ({
  getVapidKey: vi.fn(),
  listPushDevices: vi.fn(),
  subscribePush: vi.fn(),
  unsubscribePush: vi.fn(),
  renamePushDevice: vi.fn(),
  removePushDevice: vi.fn(),
}));
vi.mock("@/lib/api/push", () => api);
vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));

import { PushDevices } from "@/components/settings/PushDevices";
import { endpointHash } from "@/hooks/usePushNotifications";
import { renderWithProviders } from "../../utils/renderWithProviders";

const dev = (id: string, name: string, endpoint_hash: string) => ({
  id,
  name,
  endpoint_hash,
  created_at: "2026-11-01T00:00:00Z",
  last_used_at: null,
});

async function browser(endpoint: string | null) {
  const sub = endpoint ? { endpoint, unsubscribe: vi.fn() } : null;
  vi.stubGlobal("PushManager", class {});
  vi.stubGlobal("Notification", {
    permission: "granted",
    requestPermission: vi.fn(),
  });
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: {
      ready: Promise.resolve({
        pushManager: { getSubscription: async () => sub },
      }),
    },
  });
  return endpoint ? endpointHash(endpoint) : null;
}

describe("PushDevices", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => {
    vi.unstubAllGlobals();
    delete (navigator as any).serviceWorker;
  });

  it("marks this device, shows Active", async () => {
    const h = await browser("https://p/1");
    api.listPushDevices.mockResolvedValue([
      dev("a", "Pixel", h!),
      dev("b", "Laptop", "ffff"),
    ]);
    renderWithProviders(<PushDevices />);
    expect(
      await screen.findByText("This device", { selector: "span" }),
    ).toBeTruthy();
    expect(await screen.findByText("Active")).toBeTruthy();
    expect(screen.getByLabelText("Remove Laptop")).toBeTruthy();
  });

  it("second device shows Turn on, not Active", async () => {
    await browser("https://p/2");
    api.listPushDevices.mockResolvedValue([dev("b", "Laptop", "ffff")]);
    renderWithProviders(<PushDevices />);
    expect(await screen.findByText("Turn on for this device")).toBeTruthy();
    expect(screen.queryByText("Active")).toBeNull();
  });

  it("renames inline", async () => {
    await browser(null);
    api.listPushDevices.mockResolvedValue([dev("b", "Laptop", "ffff")]);
    api.renamePushDevice.mockResolvedValue(dev("b", "Desk", "ffff"));
    renderWithProviders(<PushDevices />);
    await userEvent.click(await screen.findByLabelText("Rename Laptop"));
    const input = screen.getByLabelText("Device name");
    await userEvent.clear(input);
    await userEvent.type(input, "Desk");
    await userEvent.click(screen.getByText("Save"));
    await waitFor(() =>
      expect(api.renamePushDevice).toHaveBeenCalledWith("b", "Desk"),
    );
  });

  it("removes another device", async () => {
    await browser(null);
    api.listPushDevices.mockResolvedValue([dev("b", "Laptop", "ffff")]);
    api.removePushDevice.mockResolvedValue(undefined);
    renderWithProviders(<PushDevices />);
    await userEvent.click(await screen.findByLabelText("Remove Laptop"));
    await waitFor(() => expect(api.removePushDevice).toHaveBeenCalledWith("b"));
  });

  it("shows the hint on iOS Chrome too", () => {
    vi.spyOn(navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) CriOS/120 Mobile Safari/604.1",
    );
    renderWithProviders(<PushDevices />);
    expect(screen.getByText(/add Nexara to your Home Screen/)).toBeTruthy();
    vi.restoreAllMocks();
  });

  it("shows the iPhone hint when not standalone", () => {
    vi.spyOn(navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1",
    );
    renderWithProviders(<PushDevices />);
    expect(
      screen.getByText(
        "On iPhone, add Nexara to your Home Screen first to get notifications.",
      ),
    ).toBeTruthy();
    vi.restoreAllMocks();
  });
});
