/**
 * @file tests/unit/auth/ssoErrors.test.ts
 * @brief SSO error codes map to fixed copy; the callback page route exists.
 */
import { describe, it, expect } from "vitest";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { ssoErrorMessage } from "@/lib/auth/ssoErrors";

describe("ssoErrorMessage", () => {
  it("maps sso_failed explicitly", () => {
    expect(ssoErrorMessage("sso_failed")).toBe(
      "Single sign-on didn't work. Please try again.",
    );
  });

  it("sso_email_unverified names the provider and points to an admin", () => {
    expect(ssoErrorMessage("sso_email_unverified", "Authentik")).toBe(
      "Your Authentik account's email isn't verified. Ask an admin to check the provider settings.",
    );
  });

  it("sso_email_taken has its own copy", () => {
    expect(ssoErrorMessage("sso_email_taken")).toMatch(/removed account/);
  });
});

describe("SSO landing contract", () => {
  it("the backend success redirect target /callback exists (app/(auth)/callback)", () => {
    // Route groups do not appear in the URL: backend redirects to {base}/callback?code=.
    expect(
      existsSync(resolve(__dirname, "../../../app/(auth)/callback/page.tsx")),
    ).toBe(true);
    expect(existsSync(resolve(__dirname, "../../../app/auth/callback"))).toBe(
      false,
    );
  });
});
