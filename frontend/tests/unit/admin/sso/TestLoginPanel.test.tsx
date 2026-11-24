/**
 * @file tests/unit/admin/sso/TestLoginPanel.test.tsx
 * @brief Test-login popup flow: start, receive result id via postMessage, render report.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as api from "@/lib/api/adminOauth";
import {
  TestLoginPanel,
  describeResult,
} from "@/components/admin/sso/TestLoginPanel";
import type { TestLoginResult } from "@/lib/api/adminOauth";

vi.mock("@/lib/api/adminOauth", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/adminOauth")>()),
  startTestLogin: vi.fn(),
  readTestLogin: vi.fn(),
}));

const RESULT: TestLoginResult = {
  provider_id: "p1",
  claims: { sub: "abc", email: "jo@smith.family", groups: ["smiths"] },
  identity: {
    sub: "abc",
    email: "jo@smith.family",
    email_verified: true,
    display_name: "Jo",
    username: "jo",
    groups: ["smiths"],
  },
  role: "member",
  role_mapped: true,
  subgroups: [{ id: "g-smith", name: "Smith Family", role: "member" }],
  outcome: { allowed: true, action: "create", code: null },
};

const popup = { location: { href: "" }, close: vi.fn() };

function post(data: unknown, origin = window.location.origin) {
  act(() => {
    window.dispatchEvent(new MessageEvent("message", { data, origin }));
  });
}

describe("TestLoginPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    popup.location.href = "";
    vi.spyOn(window, "open").mockReturnValue(popup as unknown as Window);
    vi.mocked(api.startTestLogin).mockResolvedValue({
      authorize_url: "https://idp.example/authorize?state=s",
    });
    vi.mocked(api.readTestLogin).mockResolvedValue(RESULT);
  });
  afterEach(() => vi.restoreAllMocks());

  it("asks to save first when the provider is new", () => {
    render(<TestLoginPanel providerId={null} />);
    expect(screen.getByText(/save the provider first/i)).toBeTruthy();
  });

  it("opens the IdP in a popup and renders the computed role", async () => {
    render(<TestLoginPanel providerId="p1" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Run test sign-in" }),
    );
    expect(window.open).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(popup.location.href).toBe("https://idp.example/authorize?state=s"),
    );
    expect(api.startTestLogin).toHaveBeenCalledWith("p1");
    post({ type: api.SSO_TEST_MESSAGE, result: "r1" });
    expect(
      await screen.findByText("Would be: member of Smith Family, role member"),
    ).toBeTruthy();
    expect(api.readTestLogin).toHaveBeenCalledWith("r1");
    expect(screen.getByText(/creates a new account/i)).toBeTruthy();
    expect(screen.getByLabelText("Raw claims").textContent).toContain(
      '"email": "jo@smith.family"',
    );
  });

  it("ignores messages from other origins", async () => {
    render(<TestLoginPanel providerId="p1" />);
    post({ type: api.SSO_TEST_MESSAGE, result: "r1" }, "https://evil.example");
    await new Promise((r) => setTimeout(r, 0));
    expect(api.readTestLogin).not.toHaveBeenCalled();
  });

  it("shows an error when the test cannot start", async () => {
    vi.mocked(api.startTestLogin).mockRejectedValue(new Error("nope"));
    render(<TestLoginPanel providerId="p1" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Run test sign-in" }),
    );
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(popup.close).toHaveBeenCalled();
  });
});

describe("describeResult", () => {
  it("explains a gate refusal", () => {
    expect(
      describeResult({
        ...RESULT,
        outcome: { allowed: false, action: null, code: "sso_group_required" },
      }),
    ).toBe("Would be refused: user is not in the required group");
  });

  it("role only when no groups map", () => {
    expect(describeResult({ ...RESULT, subgroups: [], role: "viewer" })).toBe(
      "Would be: role viewer",
    );
  });
});
