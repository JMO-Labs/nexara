'use client';
/**
 * @file components/admin/AdminSettingsTab.tsx
 * @brief Global admin settings form.
 */
import { useState, useEffect } from 'react';
import {
  useAdminSettings,
  useUpdateAdminSettings,
} from '@/hooks/useAdmin';
import Stack from '@mui/joy/Stack';
import Card from '@mui/joy/Card';
import Button from '@mui/joy/Button';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import Switch from '@mui/joy/Switch';
import Input from '@mui/joy/Input';
import Typography from '@mui/joy/Typography';
import CircularProgress from '@mui/joy/CircularProgress';
import Alert from '@mui/joy/Alert';

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
    <Card variant="outlined" sx={{ maxWidth: 600 }}>
      <form onSubmit={handleSubmit}>
        <Stack spacing={3}>
          <div>
            <Typography level="h4">Registration & Access</Typography>
          </div>

          <FormControl>
            <FormLabel>Enable Registration</FormLabel>
            <Typography level="body-sm" textColor="text.tertiary" sx={{ mb: 1 }}>
              Allow new users to create accounts
            </Typography>
            <Switch
              checked={enableReg}
              onChange={(e) => {
                setEnableReg(e.target.checked);
                handleChange();
              }}
            />
          </FormControl>

          <FormControl>
            <FormLabel>Require Invite</FormLabel>
            <Typography level="body-sm" textColor="text.tertiary" sx={{ mb: 1 }}>
              Users must have an invite code to join
            </Typography>
            <Switch
              checked={requireInvite}
              onChange={(e) => {
                setRequireInvite(e.target.checked);
                handleChange();
              }}
            />
          </FormControl>

          <div>
            <Typography level="h4">Storage & System</Typography>
          </div>

          <FormControl>
            <FormLabel>Default Storage Quota (bytes)</FormLabel>
            <Typography level="body-sm" textColor="text.tertiary" sx={{ mb: 1 }}>
              Default media storage limit per user
            </Typography>
            <Input
              type="number"
              value={storageQuota}
              onChange={(e) => {
                setStorageQuota(Number(e.target.value));
                handleChange();
              }}
              slotProps={{ input: { min: 0 } }}
            />
          </FormControl>

          <div>
            <Typography level="h4">Security</Typography>
          </div>

          <FormControl>
            <FormLabel>Enable WAF</FormLabel>
            <Typography level="body-sm" textColor="text.tertiary" sx={{ mb: 1 }}>
              Web Application Firewall protection
            </Typography>
            <Switch
              checked={wafEnabled}
              onChange={(e) => {
                setWafEnabled(e.target.checked);
                handleChange();
              }}
            />
          </FormControl>

          <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
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
            >
              Reset
            </Button>
            <Button
              type="submit"
              disabled={!isDirty}
              loading={updateMutation.isPending}
            >
              Save Changes
            </Button>
          </Stack>
        </Stack>
      </form>
    </Card>
  );
}
