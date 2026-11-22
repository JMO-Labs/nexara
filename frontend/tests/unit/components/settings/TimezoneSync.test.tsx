/**
 * @file tests/unit/components/settings/TimezoneSync.test.tsx
 * @brief TimezoneSync PATCHes the browser zone only when none is saved.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import * as users from "@/lib/api/users";
import { useSession } from "@/stores/session";
import { TimezoneSync } from "@/components/settings/TimezoneSync";

vi.mock("@/lib/api/users", () => ({ patchMe: vi.fn() }));

const base = {
  id: "u",
  email: "a@b.c",
  username: "a",
  display_name: "A",
} as unknown as users.CurrentUser;

describe("TimezoneSync", () => {
  beforeEach(() => vi.clearAllMocks());

  it("patches when timezone is null", async () => {
    vi.mocked(users.patchMe).mockResolvedValue({ ...base, timezone: "UTC" });
    useSession.getState().setUser({ ...base, timezone: null });
    render(<TimezoneSync />);
    await waitFor(() => expect(users.patchMe).toHaveBeenCalledTimes(1));
    expect(users.patchMe).toHaveBeenCalledWith({
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    });
  });

  it("does nothing when already set", () => {
    useSession.getState().setUser({ ...base, timezone: "America/Phoenix" });
    render(<TimezoneSync />);
    expect(users.patchMe).not.toHaveBeenCalled();
  });
});
