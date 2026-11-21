/**
 * @file wsUrl.test.ts
 * @brief deriveWsUrl must target the page origin in production builds.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

const setLocation = (href: string) => {
  const u = new URL(href);
  Object.defineProperty(window, "location", {
    value: { protocol: u.protocol, hostname: u.hostname, host: u.host },
    configurable: true,
  });
};

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("deriveWsUrl", () => {
  it("uses the page host in production even on localhost", async () => {
    vi.stubEnv("NODE_ENV", "production");
    setLocation("http://localhost:8090/app/chat");
    const { deriveWsUrl } = await import("@/lib/realtime/chat-ws");
    expect(deriveWsUrl()).toBe("ws://localhost:8090/ws/");
  });

  it("targets the backend dev port in development on localhost", async () => {
    vi.stubEnv("NODE_ENV", "development");
    setLocation("http://localhost:3000/app/chat");
    const { deriveWsUrl } = await import("@/lib/realtime/chat-ws");
    expect(deriveWsUrl()).toBe("ws://localhost:8000/ws/");
  });

  it("uses wss on https hosts", async () => {
    vi.stubEnv("NODE_ENV", "production");
    setLocation("https://nexara.example.org/app");
    const { deriveWsUrl } = await import("@/lib/realtime/chat-ws");
    expect(deriveWsUrl()).toBe("wss://nexara.example.org/ws/");
  });
});
