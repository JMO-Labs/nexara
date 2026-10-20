"use client";
/**
 * @file components/admin/AdminSettingsTab.tsx
 * @brief Global admin settings form.
 */
import { useState, useEffect } from "react";
import { useAdminSettings, useUpdateAdminSettings } from "@/hooks/useAdmin";
import Stack from "@mui/joy/Stack";
import Button from "@mui/joy/Button";
import Switch from "@mui/joy/Switch";
import Input from "@mui/joy/Input";
import Typography from "@mui/joy/Typography";
import CircularProgress from "@mui/joy/CircularProgress";
import Alert from "@mui/joy/Alert";
import { Card, SettingsRow } from "@/components/ui";

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
    return (
      <Stack alignItems="center" justifyContent="center" sx={{ py: 8 }}>
        <CircularProgress />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert color="danger" variant="soft">
        Failed to load admin settings
      </Alert>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <Stack spacing={3} sx={{ maxWidth: 800 }}>
        {/* Registration & Access */}
        <Card variant="outlined">
          <Typography level="title-md" component="h2" sx={{ mb: 2 }}>
            Registration & Access
          </Typography>
          <Stack spacing={1.5}>
            <SettingsRow
              label="Enable Registration"
              description="Allow new users to create accounts"
            >
              <Switch
                checked={enableReg}
                onChange={(e) => {
                  setEnableReg(e.target.checked);
                  handleChange();
                }}
                size="sm"
              />
            </SettingsRow>
            <SettingsRow
              label="Require Invite"
              description="Users must have an invite code to join"
            >
              <Switch
                checked={requireInvite}
                onChange={(e) => {
                  setRequireInvite(e.target.checked);
                  handleChange();
                }}
                size="sm"
              />
            </SettingsRow>
          </Stack>
        </Card>

        {/* Storage & System */}
        <Card variant="outlined">
          <Typography level="title-md" component="h2" sx={{ mb: 2 }}>
            Storage & System
          </Typography>
          <SettingsRow
            label="Default Storage Quota"
            description="Maximum media storage limit per user (in bytes)"
          >
            <Input
              type="number"
              value={storageQuota}
              onChange={(e) => {
                setStorageQuota(Number(e.target.value));
                handleChange();
              }}
              slotProps={{ input: { min: 0 } }}
              size="sm"
            />
          </SettingsRow>
        </Card>

        {/* Security */}
        <Card variant="outlined">
          <Typography level="title-md" component="h2" sx={{ mb: 2 }}>
            Security
          </Typography>
          <SettingsRow
            label="Enable WAF"
            description="Web Application Firewall protection against common attacks"
          >
            <Switch
              checked={wafEnabled}
              onChange={(e) => {
                setWafEnabled(e.target.checked);
                handleChange();
              }}
              size="sm"
            />
          </SettingsRow>
        </Card>

        {/* Actions */}
        <Stack direction="row" spacing={2}>
          <Button
            variant="soft"
            color="neutral"
            onClick={() => {
              if (settings) {
                setEnableReg(settings.enable_registration);
                setRequireInvite(settings.require_invite);
                setStorageQuota(settings.storage_quota_default);
                setWafEnabled(settings.waf_enabled);
                setIsDirty(false);
              }
            }}
            size="sm"
          >
            Reset
          </Button>
          <Button
            type="submit"
            disabled={!isDirty}
            loading={updateMutation.isPending}
            size="sm"
          >
            Save Changes
          </Button>
        </Stack>
      </Stack>
    </form>
  );
}
