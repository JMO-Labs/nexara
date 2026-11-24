"use client";
/**
 * @file components/admin/AdminSettingsTab.tsx
 * @brief Global admin settings form: one Panel per group, right-aligned controls.
 */
import { useState, type ReactNode } from "react";
import { useAdminSettings, useUpdateAdminSettings } from "@/hooks/useAdmin";
import { Button, Input, Switch } from "@/components/ui";
import { Panel, Segmented } from "@/components/ui/page";
import { formatBytes } from "@/lib/formatBytes";
import type { AdminSettingsResponse } from "@/lib/api/admin";
import { AdminLoading, AdminNotice } from "./AdminState";
import { CurrencySetting } from "./CurrencySetting";
import { OnboardingSettings } from "./OnboardingSettings";

const MB = 1024 ** 2;
const GB = 1024 ** 3;

const DEFAULTS: AdminSettingsResponse = {
  enable_registration: true,
  require_invite: false,
  storage_quota_default: 5000000000,
  waf_enabled: true,
};

/**
 * @brief Setting row: label and help on the left, control right-aligned.
 * @param label setting name
 * @param description one-line help
 * @param children control
 * @return row element
 */
function Row({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 py-2">
      <div className="min-w-0">
        <p className="text-sm font-medium">{label}</p>
        {description && (
          <p className="mt-0.5 text-xs text-muted">{description}</p>
        )}
      </div>
      <div className="flex items-center">{children}</div>
    </div>
  );
}

export function AdminSettingsTab() {
  // Local edits layered over server values (derived, no sync effect).
  const [draft, setDraft] = useState<Partial<AdminSettingsResponse>>({});
  const [isDirty, setIsDirty] = useState(false);
  const [unit, setUnit] = useState<"MB" | "GB" | null>(null);

  const { data: settings, isLoading, error } = useAdminSettings();
  const updateMutation = useUpdateAdminSettings();

  const form: AdminSettingsResponse = {
    ...DEFAULTS,
    ...settings,
    ...draft,
  };
  const enableReg = form.enable_registration;
  const requireInvite = form.require_invite;
  const storageQuota = form.storage_quota_default;
  const wafEnabled = form.waf_enabled;
  // Show GB for quotas of 1 GB or more unless the admin picked a unit.
  const shownUnit = unit ?? (storageQuota >= GB ? "GB" : "MB");
  const scale = shownUnit === "GB" ? GB : MB;

  const edit = (patch: Partial<AdminSettingsResponse>) => {
    setDraft((d) => ({ ...d, ...patch }));
    setIsDirty(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(
      {
        enable_registration: enableReg,
        require_invite: requireInvite,
        storage_quota_default: storageQuota,
        waf_enabled: wafEnabled,
      },
      // Drop the draft once saved so later server data is not masked.
      { onSuccess: () => setDraft({}) },
    );
    setIsDirty(false);
  };

  if (isLoading) {
    return <AdminLoading />;
  }

  if (error) {
    return (
      <AdminNotice tone="error">Failed to load admin settings</AdminNotice>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <Panel as="div" title="Registration and access">
        <div className="flex flex-col gap-1">
          <Row
            label="Enable registration"
            description="Allow new users to create accounts"
          >
            <Switch
              checked={enableReg}
              aria-label="Enable registration"
              onCheckedChange={(v) => {
                edit({ enable_registration: v });
              }}
            />
          </Row>
          <Row
            label="Require invite"
            description="Users must have an invite code to join"
          >
            <Switch
              checked={requireInvite}
              aria-label="Require invite"
              onCheckedChange={(v) => {
                edit({ require_invite: v });
              }}
            />
          </Row>
        </div>
      </Panel>

      <Panel as="div" title="Storage and system">
        <Row
          label="Default storage quota"
          description="Maximum media storage per user"
        >
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Input
              type="number"
              step="any"
              value={Number((storageQuota / scale).toFixed(4))}
              onChange={(e) => {
                edit({
                  storage_quota_default: Math.round(
                    Number(e.target.value) * scale,
                  ),
                });
              }}
              min={0}
              aria-label="Default storage quota"
              className="w-28"
            />
            <Segmented
              label="Quota unit"
              options={[
                { value: "MB", label: "MB" },
                { value: "GB", label: "GB" },
              ]}
              value={shownUnit}
              onChange={setUnit}
            />
          </div>
        </Row>
        <p className="mt-1 text-right text-xs text-muted">
          {formatBytes(storageQuota)} per user
        </p>
      </Panel>

      <CurrencySetting />

      <OnboardingSettings />

      <Panel as="div" title="Security">
        <Row
          label="Enable WAF"
          description="Web Application Firewall protection against common attacks"
        >
          <Switch
            checked={wafEnabled}
            aria-label="Enable WAF"
            onCheckedChange={(v) => {
              edit({ waf_enabled: v });
            }}
          />
        </Row>
      </Panel>

      <div className="flex justify-end gap-3">
        <Button
          variant="glass"
          type="button"
          onClick={() => {
            setDraft({});
            setIsDirty(false);
          }}
        >
          Reset
        </Button>
        <Button
          type="submit"
          disabled={!isDirty}
          loading={updateMutation.isPending}
        >
          Save changes
        </Button>
      </div>
    </form>
  );
}
