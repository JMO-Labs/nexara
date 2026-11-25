/**
 * @file tests/unit/admin/SigninsTab.test.tsx
 * @brief SigninsTab: rows, failure reason, filter query, paging and CSV export.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders as render } from "../../utils/renderWithProviders";

vi.mock("@/lib/api/signins", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/signins")>()),
  listSignins: vi.fn(),
  exportSigninsCsv: vi.fn(),
}));
import * as api from "@/lib/api/signins";
import { SigninsTab } from "@/components/admin/SigninsTab";

const row = (id: string, over = {}) => ({
  id,
  time: "2026-01-02T03:04:05Z",
  email: "a@x.dev",
  user: "ana",
  method: "password",
  success: true,
  reason: null,
  ip: "1.2.3.4",
  device: "Chrome on Linux",
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listSignins).mockResolvedValue({
    items: [
      row("1"),
      row("2", { success: false, reason: "bad_password" }),
      row("3", { success: false, reason: "bad_2fa_session" }),
    ],
    next_cursor: "c1",
  });
  URL.createObjectURL = vi.fn(() => "blob:x");
  URL.revokeObjectURL = vi.fn();
});

describe("SigninsTab", () => {
  it("lists rows with failure reason and pages on demand", async () => {
    render(<SigninsTab />);
    expect(await screen.findByText("Failed (bad password)")).toBeTruthy();
    expect(screen.getByText("Failed (bad 2fa session)")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Load more" }));
    await waitFor(() =>
      expect(vi.mocked(api.listSignins).mock.calls.at(-1)?.[1]).toBe("c1"),
    );
  });

  it("sends the search text and exports with the same filters", async () => {
    vi.mocked(api.exportSigninsCsv).mockResolvedValue("time,email\n");
    render(<SigninsTab />);
    await screen.findByText("Failed (bad password)");
    await userEvent.type(screen.getByRole("searchbox"), "10.0");
    await waitFor(() =>
      expect(vi.mocked(api.listSignins).mock.calls.at(-1)?.[0].q).toBe("10.0"),
    );
    await userEvent.click(screen.getByRole("button", { name: /Export CSV/ }));
    await waitFor(() =>
      expect(vi.mocked(api.exportSigninsCsv).mock.calls[0][0].q).toBe("10.0"),
    );
  });
});

describe("signinQuery", () => {
  it("drops empty filters", () => {
    expect(api.signinQuery({ q: "", success: "", method: "", since: "" })).toBe(
      "",
    );
    expect(
      api.signinQuery(
        { q: " a b ", success: "false", method: "sso", since: "" },
        "c",
      ),
    ).toBe("?q=a+b&success=false&method=sso&cursor=c");
    expect(
      api.signinQuery({ q: "", success: "", method: "", since: "2026-01-02" }),
    ).toMatch(/^\?since=2026-01-0[12]T/);
  });
});
