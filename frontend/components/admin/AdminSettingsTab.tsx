"use client";
/**
 * @file components/admin/AdminSettingsTab.tsx
 * @brief Global admin settings form.
 */
import { useState, useEffect } from "react";
import { useAdminSettings, useUpdateAdminSettings } from "@/hooks/useAdmin";
import { Button, Card, Input, SettingsRow, Switch } from "@/components/ui";
import { AdminLoading, AdminNotice } from "./AdminState";

export function AdminSettingsTab() {
  const [enableReg, setEnableReg] = useState(true);
  const [requireInvite, setRequireInvite] = useState(false);
  const [storageQuota, setStorageQuota] = useState(5000000000);
  const [wafEnabled, setWafEnabled] = useState(true);
  const [isDirty, setIsDirty] = useState(false);

  const { data: settings, isLoading, error } = useAdminSettings();
  const updateMutation = useUpdateAdminSettings();

  useEffect(() => {
    // Sync form state from fetched server settings on load.
    if (settings) {
      /* eslint-disable react-hooks/set-state-in-effect */
      setEnableReg(settings.enable_registration);
      setRequireInvite(settings.require_invite);
      setStorageQuota(settings.storage_quota_default);
      setWafEnabled(settings.waf_enabled);
      setIsDirty(false);
      /* eslint-enable react-hooks/set-state-in-effect */
    }
  }, [settings]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({
      enable_registration: enableReg,
      require_invite: requireInvite,
      storage_quota_default: storageQuota,
      waf_enabled: wafEnabled,
    });
    setIsDirty(false);
  };

  const handleChange = () => {
    setIsDirty(true);
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
                  setEnableReg(v);
                  handleChange();
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
                  setRequireInvite(v);
                  handleChange();
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
                setStorageQuota(Number(e.target.value));
                handleChange();
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
                setWafEnabled(v);
                handleChange();
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
              if (settings) {
                setEnableReg(settings.enable_registration);
                setRequireInvite(settings.require_invite);
                setStorageQuota(settings.storage_quota_default);
                setWafEnabled(settings.waf_enabled);
                setIsDirty(false);
              }
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
