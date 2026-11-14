/**
 * @file tests/unit/admin/AdminSettingsTab.test.tsx
 * @brief Form shows server values, tracks edits, resets and submits.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import * as admin from "@/hooks/useAdmin";
import { AdminSettingsTab } from "@/components/admin/AdminSettingsTab";

vi.mock("@/hooks/useAdmin");

const server = {
  enable_registration: true,
  require_invite: false,
  storage_quota_default: 1000,
  waf_enabled: true,
};
const mutate = vi.fn();

const quota = () =>
  screen.getByLabelText("Default storage quota in bytes") as HTMLInputElement;
const save = () => screen.getByRole("button", { name: /save changes/i });

describe("AdminSettingsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(admin.useAdminSettings).mockReturnValue({
      data: server,
      isLoading: false,
      error: null,
    } as any);
    vi.mocked(admin.useUpdateAdminSettings).mockReturnValue({
      mutate,
      isPending: false,
    } as any);
  });

  it("renders server values with save disabled", () => {
    render(<AdminSettingsTab />);
    expect(quota().value).toBe("1000");
    expect(save()).toBeDisabled();
  });

  it("submits edited values merged with server values", () => {
    render(<AdminSettingsTab />);
    fireEvent.change(quota(), { target: { value: "2000" } });
    expect(save()).toBeEnabled();
    fireEvent.click(save());
    expect(mutate).toHaveBeenCalledWith(
      { ...server, storage_quota_default: 2000 },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("reset restores server values", () => {
    render(<AdminSettingsTab />);
    fireEvent.change(quota(), { target: { value: "2000" } });
    fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    expect(quota().value).toBe("1000");
    expect(save()).toBeDisabled();
  });

  it("follows refetched server values when not edited", () => {
    const { rerender } = render(<AdminSettingsTab />);
    vi.mocked(admin.useAdminSettings).mockReturnValue({
      data: { ...server, storage_quota_default: 3000 },
      isLoading: false,
      error: null,
    } as any);
    rerender(<AdminSettingsTab />);
    expect(quota().value).toBe("3000");
  });

  it("clears the draft after save so new server data shows", () => {
    const { rerender } = render(<AdminSettingsTab />);
    fireEvent.change(quota(), { target: { value: "2000" } });
    fireEvent.click(save());
    const opts = mutate.mock.calls[0][1];
    act(() => opts.onSuccess());
    vi.mocked(admin.useAdminSettings).mockReturnValue({
      data: { ...server, storage_quota_default: 4000 },
      isLoading: false,
      error: null,
    } as any);
    rerender(<AdminSettingsTab />);
    expect(quota().value).toBe("4000");
  });
});
