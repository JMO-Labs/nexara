/**
 * @file tests/unit/components/admin/AdminTabStates.test.tsx
 * @brief Loading and error states for the remaining admin tabs.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import * as admin from "@/hooks/useAdmin";
import * as invites from "@/hooks/useInvites";
import * as oauth from "@/hooks/useAdminOauth";
import { MetricsTab } from "@/components/admin/MetricsTab";
import { InvitesTab } from "@/components/admin/InvitesTab";
import { SsoTab } from "@/components/admin/SsoTab";
import { AdminSettingsTab } from "@/components/admin/AdminSettingsTab";
import { AuditLogTab } from "@/components/admin/AuditLogTab";

vi.mock("@/hooks/useAdmin");
vi.mock("@/hooks/useInvites");
vi.mock("@/hooks/useAdminOauth");

const mut = { mutate: vi.fn(), isPending: false } as any;
const cases: [string, any, any, RegExp][] = [
  [
    "Metrics",
    MetricsTab,
    () => admin.useAdminMetrics,
    /failed to load metrics/i,
  ],
  ["Invites", InvitesTab, () => invites.useInvites, /failed to load invites/i],
  ["Sso", SsoTab, () => oauth.useOauthProviders, /failed to load oauth/i],
  [
    "Settings",
    AdminSettingsTab,
    () => admin.useAdminSettings,
    /failed to load admin settings/i,
  ],
  [
    "AuditLog",
    AuditLogTab,
    () => admin.useAuditLog,
    /failed to load audit log/i,
  ],
];

beforeEach(() => {
  vi.clearAllMocks();
  for (const m of [admin, invites, oauth] as any[])
    for (const k of Object.keys(m))
      if (/^use/.test(k) && vi.isMockFunction(m[k])) m[k].mockReturnValue(mut);
});

describe.each(cases)("%s tab", (_n, Tab, hook, errRe) => {
  it("shows a loading status", () => {
    vi.mocked(hook()).mockReturnValue({ isLoading: true } as any);
    render(<Tab />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
  it("shows an error alert", () => {
    vi.mocked(hook()).mockReturnValue({
      isLoading: false,
      error: new Error("x"),
    } as any);
    render(<Tab />);
    expect(screen.getByRole("alert")).toHaveTextContent(errRe);
  });
});
