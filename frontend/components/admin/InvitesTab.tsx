'use client';
/**
 * @file components/admin/InvitesTab.tsx
 * @brief Admin invite creation and management.
 */
import { useState } from 'react';
import { useInvites, useCreateInvite, useRevokeInvite } from '@/hooks/useInvites';
import Stack from '@mui/joy/Stack';
import Input from '@mui/joy/Input';
import Select from '@mui/joy/Select';
import Option from '@mui/joy/Option';
import Button from '@mui/joy/Button';
import IconButton from '@mui/joy/IconButton';
import Card from '@mui/joy/Card';
import Table from '@mui/joy/Table';
import Typography from '@mui/joy/Typography';
import CircularProgress from '@mui/joy/CircularProgress';
import Alert from '@mui/joy/Alert';
import { TrashIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';

export function InvitesTab() {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<string>('member');

  const { data: invites, isLoading, error } = useInvites();
  const createMutation = useCreateInvite();
  const revokeMutation = useRevokeInvite();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      createMutation.mutate({ email, role });
      setEmail('');
      setRole('member');
    }
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
        Failed to load invites
      </Alert>
    );
  }

  return (
    <Stack spacing={4}>
      <Card variant="soft">
        <Stack spacing={2}>
          <Typography level="h4">Create Invite</Typography>
          <form onSubmit={handleSubmit}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <Input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                sx={{ flex: 1 }}
              />
              <Select
                value={role}
                onChange={(_, val) => val && setRole(val)}
                sx={{ minWidth: 120 }}
              >
                <Option value="admin">Admin</Option>
                <Option value="member">Member</Option>
                <Option value="viewer">Viewer</Option>
              </Select>
              <Button
                type="submit"
                loading={createMutation.isPending}
                sx={{ minWidth: 100 }}
              >
                Send Invite
              </Button>
            </Stack>
          </form>
        </Stack>
      </Card>

      {invites && invites.length > 0 ? (
        <Card variant="outlined">
          <Table
            stripe="odd"
            hoverRow
            sx={{
              '--TableCell-paddingX': '1rem',
              '--TableCell-paddingY': '0.5rem',
            }}
          >
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Created</th>
                <th>Expires</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invites.map((invite) => (
                <tr key={invite.id}>
                  <td>
                    <Typography level="body-sm">{invite.email}</Typography>
                  </td>
                  <td>
                    <Typography level="body-sm">{invite.role}</Typography>
                  </td>
                  <td>
                    <Typography level="body-sm">
                      {format(new Date(invite.created_at), 'MMM d, yyyy')}
                    </Typography>
                  </td>
                  <td>
                    <Typography level="body-sm">
                      {format(new Date(invite.expires_at), 'MMM d, yyyy')}
                    </Typography>
                  </td>
                  <td>
                    <Typography
                      level="body-sm"
                      color={invite.used_at ? 'success' : 'warning'}
                    >
                      {invite.used_at ? 'Used' : 'Pending'}
                    </Typography>
                  </td>
                  <td>
                    <IconButton
                      size="sm"
                      variant="soft"
                      color="danger"
                      onClick={() => revokeMutation.mutate(invite.id)}
                      loading={revokeMutation.isPending}
                      title="Revoke invite"
                    >
                      <TrashIcon width={16} height={16} />
                    </IconButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      ) : (
        <Alert color="primary" variant="soft">
          No pending invites
        </Alert>
      )}
    </Stack>
  );
}
