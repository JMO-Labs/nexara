'use client';
/**
 * @file components/admin/UsersTab.tsx
 * @brief Admin user management table with search, role editing, and actions.
 */
import { useState } from 'react';
import {
  useAdminUsers,
  useChangeUserRole,
  useSuspendUser,
  useRestoreUser,
  useDeleteUser,
} from '@/hooks/useAdmin';
import Stack from '@mui/joy/Stack';
import Input from '@mui/joy/Input';
import Button from '@mui/joy/Button';
import Select from '@mui/joy/Select';
import { IconButton } from '@/components/ui/IconButton';
import Option from '@mui/joy/Option';
import Table from '@mui/joy/Table';
import CircularProgress from '@mui/joy/CircularProgress';
import Alert from '@mui/joy/Alert';
import Modal from '@mui/joy/Modal';
import ModalDialog from '@mui/joy/ModalDialog';
import ModalClose from '@mui/joy/ModalClose';
import Typography from '@mui/joy/Typography';
import Card from '@mui/joy/Card';
import { TrashIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';

export function UsersTab() {
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const { data: usersPage, isLoading, error } = useAdminUsers({
    q: searchQuery || undefined,
    limit: 50,
  });

  const changeRoleMutation = useChangeUserRole();
  const suspendMutation = useSuspendUser();
  const restoreMutation = useRestoreUser();
  const deleteMutation = useDeleteUser();

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
        Failed to load users
      </Alert>
    );
  }

  if (!usersPage) return null;

  const handleRoleChange = (userId: string, role: string) => {
    changeRoleMutation.mutate({ userId, role });
  };

  const handleSuspend = (userId: string) => {
    suspendMutation.mutate(userId);
  };

  const handleRestore = (userId: string) => {
    restoreMutation.mutate(userId);
  };

  const handleDeleteClick = (userId: string) => {
    setDeletingUserId(userId);
    setDeleteConfirm(true);
  };

  const handleConfirmDelete = () => {
    if (deletingUserId) {
      deleteMutation.mutate(deletingUserId);
      setDeleteConfirm(false);
      setDeletingUserId(null);
    }
  };

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={2}>
        <Input
          placeholder="Search by name or email..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ flex: 1 }}
        />
      </Stack>

      {usersPage.items.length === 0 ? (
        <Alert color="primary" variant="soft">
          No users found
        </Alert>
      ) : (
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
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {usersPage.items.map((user) => (
                <tr key={user.id}>
                  <td>
                    <Typography level="body-sm">
                      {user.display_name || user.username}
                    </Typography>
                  </td>
                  <td>
                    <Typography level="body-sm">{user.email}</Typography>
                  </td>
                  <td>
                    <Select
                      value={user.role}
                      onChange={(_, val) =>
                        val && handleRoleChange(user.id, val as string)
                      }
                      size="sm"
                      variant="soft"
                    >
                      <Option value="admin">Admin</Option>
                      <Option value="member">Member</Option>
                      <Option value="viewer">Viewer</Option>
                    </Select>
                  </td>
                  <td>
                    <Typography level="body-sm">{user.status}</Typography>
                  </td>
                  <td>
                    <Stack direction="row" spacing={0.5}>
                      {user.status === 'active' ? (
                        <IconButton
                          tooltip="Suspend user"
                          size="sm"
                          variant="soft"
                          color="warning"
                          aria-label="Suspend user"
                          onClick={() => handleSuspend(user.id)}
                        >
                          <XMarkIcon width={16} height={16} />
                        </IconButton>
                      ) : (
                        <IconButton
                          tooltip="Restore user"
                          size="sm"
                          variant="soft"
                          color="success"
                          aria-label="Restore user"
                          onClick={() => handleRestore(user.id)}
                        >
                          <CheckIcon width={16} height={16} />
                        </IconButton>
                      )}
                      <IconButton
                        tooltip="Delete user"
                        size="sm"
                        variant="soft"
                        color="danger"
                        aria-label="Delete user"
                        onClick={() => handleDeleteClick(user.id)}
                      >
                        <TrashIcon width={16} height={16} />
                      </IconButton>
                    </Stack>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}

      <Modal
        aria-labelledby="delete-modal"
        open={deleteConfirm}
        onClose={() => setDeleteConfirm(false)}
      >
        <ModalDialog>
          <ModalClose variant="plain" sx={{ m: 1 }} />
          <Typography
            component="h2"
            id="delete-modal"
            level="inherit"
            fontSize="1.25em"
            mb="0.25em"
          >
            Delete User
          </Typography>
          <Typography level="body-sm" textColor="text.tertiary">
            Are you sure? This action cannot be undone.
          </Typography>
          <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
            <Button
              variant="plain"
              color="neutral"
              onClick={() => setDeleteConfirm(false)}
            >
              Cancel
            </Button>
            <Button
              variant="solid"
              color="danger"
              onClick={handleConfirmDelete}
              loading={deleteMutation.isPending}
            >
              Delete
            </Button>
          </Stack>
        </ModalDialog>
      </Modal>
    </Stack>
  );
}
