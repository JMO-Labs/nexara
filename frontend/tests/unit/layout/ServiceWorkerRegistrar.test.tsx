/**
 * @file tests/unit/layout/ServiceWorkerRegistrar.test.tsx
 * @brief ServiceWorkerRegistrar: registers /sw.js when supported (prod only).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ServiceWorkerRegistrar from "@/components/layout/ServiceWorkerRegistrar";
import { renderWithProviders } from "../../utils/renderWithProviders";

describe("ServiceWorkerRegistrar", () => {
  const register = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    register.mockClear();
    vi.stubEnv("NODE_ENV", "production");
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    Reflect.deleteProperty(navigator, "serviceWorker");
  });

  it("registers /sw.js when supported", () => {
    Object.defineProperty(navigator, "serviceWorker", {
      value: { register },
      configurable: true,
    });
    renderWithProviders(<ServiceWorkerRegistrar />);
    expect(register).toHaveBeenCalledWith("/sw.js", { scope: "/" });
  });

  it("is a no-op when unsupported", () => {
    renderWithProviders(<ServiceWorkerRegistrar />);
    expect(register).not.toHaveBeenCalled();
  });

  it("is a no-op outside production", () => {
    vi.stubEnv("NODE_ENV", "development");
    Object.defineProperty(navigator, "serviceWorker", {
      value: { register },
      configurable: true,
    });
    renderWithProviders(<ServiceWorkerRegistrar />);
    expect(register).not.toHaveBeenCalled();
  });
});
