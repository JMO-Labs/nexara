/**
 * @file tests/unit/admin/sso/SsoTestPage.test.tsx
 * @brief /sso-test popup posts the result id to its opener (same origin) and closes.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import SsoTestPage from "@/app/(auth)/sso-test/page";
import { SSO_TEST_MESSAGE } from "@/lib/api/adminOauth";

let search = "result=r1";
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(search),
}));

const setOpener = (v: unknown) =>
  Object.defineProperty(window, "opener", { value: v, configurable: true });

describe("SsoTestPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    setOpener(null);
    search = "result=r1";
  });

  it("forwards a failed test (fixed code only) to the opener", () => {
    search = "error=sso_failed";
    const opener = { postMessage: vi.fn() };
    setOpener(opener);
    vi.spyOn(window, "close").mockImplementation(() => {});
    render(<SsoTestPage />);
    expect(opener.postMessage).toHaveBeenCalledWith(
      { type: SSO_TEST_MESSAGE, error: "sso_failed" },
      window.location.origin,
    );
    expect(screen.getByRole("status").textContent).toMatch(/failed/i);
  });

  it("ignores unknown error values", () => {
    search = "error=<script>";
    const opener = { postMessage: vi.fn() };
    setOpener(opener);
    render(<SsoTestPage />);
    expect(opener.postMessage).not.toHaveBeenCalled();
  });

  it("posts to the opener with the own origin and closes", () => {
    const opener = { postMessage: vi.fn() };
    setOpener(opener);
    const close = vi.spyOn(window, "close").mockImplementation(() => {});
    render(<SsoTestPage />);
    expect(opener.postMessage).toHaveBeenCalledWith(
      { type: SSO_TEST_MESSAGE, result: "r1" },
      window.location.origin,
    );
    expect(close).toHaveBeenCalled();
  });

  it("without an opener tells the admin to go back", () => {
    setOpener(null);
    render(<SsoTestPage />);
    expect(screen.getByRole("status").textContent).toMatch(
      /return to the admin page/i,
    );
  });
});
