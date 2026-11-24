/**
 * @file tests/unit/auth/passkeysLib.test.ts
 * @brief authenticateWithPasskey forwards the pending 2FA token to options.
 */
import { describe, it, expect, vi } from "vitest";

vi.mock("@simplewebauthn/browser", () => ({
  startAuthentication: vi.fn().mockResolvedValue({ id: "c" }),
  startRegistration: vi.fn(),
}));
vi.mock("@/lib/api/twoFactor", () => ({
  passkeyLoginOptions: vi.fn().mockResolvedValue({ challenge: "x" }),
  passkeyLoginVerify: vi.fn().mockResolvedValue({}),
}));
vi.mock("@/lib/auth/session", () => ({ refreshAccessToken: vi.fn() }));

import { authenticateWithPasskey } from "@/lib/passkeys";
import * as api from "@/lib/api/twoFactor";

describe("authenticateWithPasskey", () => {
  it("sends the pending token to options and verify", async () => {
    await authenticateWithPasskey({ pendingToken: "T" });
    expect(api.passkeyLoginOptions).toHaveBeenCalledWith(undefined, "T");
    expect(api.passkeyLoginVerify).toHaveBeenCalledWith({ id: "c" }, "T");
  });
});
