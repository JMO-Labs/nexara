/**
 * @file tests/unit/settings/YourDevices.test.tsx
 * @brief YourDevices: current marker, per-device and "everywhere else" sign-out with confirm.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders as render } from "../../utils/renderWithProviders";

vi.mock("@/lib/api/signins");
import * as api from "@/lib/api/signins";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { YourDevices } from "@/components/settings/security/YourDevices";

const sessions = [
  {
    family_id: "f1",
    device: "Chrome on Linux",
    ip: "10.0.0.1",
    last_seen: "2026-01-01T00:00:00Z",
    current: true,
  },
  {
    family_id: "f2",
    device: "Safari on iOS",
    ip: null,
    last_seen: "2026-01-01T00:00:00Z",
    current: false,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listSessions).mockResolvedValue(sessions);
  vi.mocked(api.revokeSession).mockResolvedValue({ message: "ok" });
  vi.mocked(api.revokeOtherSessions).mockResolvedValue({ message: "ok" });
});

describe("YourDevices", () => {
  it("shows a loading status, then an alert on error", async () => {
    vi.mocked(api.listSessions).mockReturnValue(new Promise(() => {}));
    const { unmount } = render(<YourDevices />);
    expect(screen.getByRole("status").textContent).toMatch(/Loading devices/);
    unmount();
    vi.mocked(api.listSessions).mockRejectedValue(new Error("boom"));
    render(<YourDevices />);
    expect((await screen.findByRole("alert")).textContent).toMatch(
      /Could not load devices/,
    );
  });

  it("disables a device's sign-out button while it is pending", async () => {
    vi.mocked(api.revokeSession).mockReturnValue(new Promise(() => {}));
    render(
      <>
        <YourDevices />
        <ConfirmDialog />
      </>,
    );
    const btn = await screen.findByLabelText("Sign out Safari on iOS");
    await userEvent.click(btn);
    await userEvent.click(await screen.findByTestId("confirm-dialog-confirm"));
    await waitFor(() =>
      expect(
        (screen.getByLabelText("Sign out Safari on iOS") as HTMLButtonElement)
          .disabled,
      ).toBe(true),
    );
  });

  it("marks the current device and offers sign-out only for others", async () => {
    render(<YourDevices />);
    expect(await screen.findByText("This device")).toBeTruthy();
    expect(screen.queryByLabelText("Sign out Chrome on Linux")).toBeNull();
    expect(screen.getByLabelText("Sign out Safari on iOS")).toBeTruthy();
  });

  it("states the sign-out delay", async () => {
    render(<YourDevices />);
    expect(await screen.findByText(/within 15 minutes/)).toBeTruthy();
  });

  it("confirms before signing out everywhere else", async () => {
    render(
      <>
        <YourDevices />
        <ConfirmDialog />
      </>,
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Sign out everywhere else" }),
    );
    expect(api.revokeOtherSessions).not.toHaveBeenCalled();
    await userEvent.click(await screen.findByTestId("confirm-dialog-confirm"));
    await waitFor(() => expect(api.revokeOtherSessions).toHaveBeenCalled());
  });

  it("signs out one device after confirm", async () => {
    render(
      <>
        <YourDevices />
        <ConfirmDialog />
      </>,
    );
    await userEvent.click(
      await screen.findByLabelText("Sign out Safari on iOS"),
    );
    await userEvent.click(await screen.findByTestId("confirm-dialog-confirm"));
    await waitFor(() =>
      expect(vi.mocked(api.revokeSession).mock.calls[0][0]).toBe("f2"),
    );
  });
});
