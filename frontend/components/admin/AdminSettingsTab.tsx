"use client";
/**
 * @file components/admin/AdminSettingsTab.tsx
 * @brief Global admin settings form.
 */
import { useState } from "react";
import { useAdminSettings, useUpdateAdminSettings } from "@/hooks/useAdmin";
import { Button, Card, Input, SettingsRow, Switch } from "@/components/ui";
import type { AdminSettingsResponse } from "@/lib/api/admin";
import { AdminLoading, AdminNotice } from "./AdminState";

const DEFAULTS: AdminSettingsResponse = {
  enable_registration: true,
  require_invite: false,
  storage_quota_default: 5000000000,
  waf_enabled: true,
};

export function AdminSettingsTab() {
  // Local edits layered over server values (derived, no sync effect).
  const [draft, setDraft] = useState<Partial<AdminSettingsResponse>>({});
  const [isDirty, setIsDirty] = useState(false);

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
    <form onSubmit={handleSubmit}>
      <div className="flex max-w-3xl flex-col gap-6">
        {/* Registration and access */}
        <Card className="p-4">
          <h2 className="mb-2 text-lg font-semibold">
            Registration and access
          </h2>
          <div className="flex flex-col gap-3">
            <SettingsRow
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
            </SettingsRow>
            <SettingsRow
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
            </SettingsRow>
          </div>
        </Card>

        {/* Storage and system */}
        <Card className="p-4">
          <h2 className="mb-2 text-lg font-semibold">Storage and system</h2>
          <SettingsRow
            label="Default storage quota"
            description="Maximum media storage limit per user (in bytes)"
          >
            <Input
              type="number"
              value={storageQuota}
              onChange={(e) => {
                edit({ storage_quota_default: Number(e.target.value) });
              }}
              min={0}
              aria-label="Default storage quota in bytes"
            />
          </SettingsRow>
        </Card>

        {/* Security */}
        <Card className="p-4">
          <h2 className="mb-2 text-lg font-semibold">Security</h2>
          <SettingsRow
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
          </SettingsRow>
        </Card>

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            variant="ghost"
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
      </div>
    </form>
  );
}
