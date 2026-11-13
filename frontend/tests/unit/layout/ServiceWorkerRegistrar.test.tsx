/**
 * @file tests/unit/layout/ServiceWorkerRegistrar.test.tsx
 * @brief Registers /sw.js in production when supported; no-op otherwise.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render } from "@testing-library/react";
import ServiceWorkerRegistrar from "@/components/layout/ServiceWorkerRegistrar";

function setSW(value: unknown) {
  Object.defineProperty(navigator, "serviceWorker", {
    value,
    configurable: true,
  });
}

describe("ServiceWorkerRegistrar", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (navigator as any).serviceWorker;
  });

  it("registers /sw.js when supported in production", () => {
    vi.stubEnv("NODE_ENV", "production");
    const register = vi.fn().mockResolvedValue({});
    setSW({ register });
    render(<ServiceWorkerRegistrar />);
    expect(register).toHaveBeenCalledWith("/sw.js", { scope: "/" });
  });

  it("does not register outside production", () => {
    vi.stubEnv("NODE_ENV", "test");
    const register = vi.fn().mockResolvedValue({});
    setSW({ register });
    render(<ServiceWorkerRegistrar />);
    expect(register).not.toHaveBeenCalled();
  });

  it("is a no-op when serviceWorker is unsupported", () => {
    vi.stubEnv("NODE_ENV", "production");
    expect(() => render(<ServiceWorkerRegistrar />)).not.toThrow();
  });
});
