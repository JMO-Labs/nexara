"use client";
/**
 * @file components/admin/UsersTab.tsx
 * @brief Admin user management table with search, role editing, and actions.
 */
import { useState } from "react";
import {
  useAdminUsers,
  useSuspendUser,
  useRestoreUser,
  useDeleteUser,
} from "@/hooks/useAdmin";
import Stack from "@mui/joy/Stack";
import Input from "@mui/joy/Input";
import Button from "@mui/joy/Button";
import Select from "@mui/joy/Select";
import Chip from "@mui/joy/Chip";
import { IconButton } from "@/components/ui/IconButton";
import Option from "@mui/joy/Option";
import Table from "@mui/joy/Table";
import CircularProgress from "@mui/joy/CircularProgress";
import Alert from "@mui/joy/Alert";
import Modal from "@mui/joy/Modal";
import ModalDialog from "@mui/joy/ModalDialog";
import ModalClose from "@mui/joy/ModalClose";
import Typography from "@mui/joy/Typography";
import Card from "@mui/joy/Card";
import { TrashIcon, CheckIcon, XMarkIcon } from "@heroicons/react/24/outline";

export function UsersTab() {
  const [searchQuery, setSearchQuery] = useState("");
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [density, setDensity] = useState<"comfortable" | "compact">(
    "comfortable",
  );

  const {
    data: usersPage,
    isLoading,
    error,
  } = useAdminUsers({
    q: searchQuery || undefined,
    limit: 50,
  });

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
      <Stack
        direction="row"
        spacing={2}
        alignItems="center"
        justifyContent="space-between"
      >
        <Input
          placeholder="Search by name or email..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ flex: 1 }}
        />
        <Select
          value={density}
          onChange={(_, val) =>
            val && setDensity(val as "comfortable" | "compact")
          }
          size="sm"
          variant="soft"
          sx={{ minWidth: 120 }}
        >
          <Option value="comfortable">Comfortable</Option>
          <Option value="compact">Compact</Option>
        </Select>
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
              "--TableCell-paddingX":
                density === "compact" ? "0.75rem" : "1rem",
              "--TableCell-paddingY":
                density === "compact" ? "0.375rem" : "0.5rem",
              fontSize: density === "compact" ? "0.85rem" : "inherit",
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
                    <Typography
                      level={density === "compact" ? "body-xs" : "body-sm"}
                    >
                      {user.display_name || user.username}
                    </Typography>
                  </td>
                  <td>
                    <Typography
                      level={density === "compact" ? "body-xs" : "body-sm"}
                    >
                      {user.email}
                    </Typography>
                  </td>
                  <td>
                    <Chip
                      size={density === "compact" ? "sm" : "md"}
                      color={
                        user.role === "admin"
                          ? "danger"
                          : user.role === "member"
                            ? "primary"
                            : "neutral"
                      }
                      variant="soft"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {user.role === "admin" && "Admin"}
                      {user.role === "member" && "Member"}
                      {user.role === "viewer" && "Viewer"}
                    </Chip>
                  </td>
                  <td>
                    <Typography
                      level={density === "compact" ? "body-xs" : "body-sm"}
                      color={user.status === "active" ? "success" : "warning"}
                    >
                      {user.status}
                    </Typography>
                  </td>
                  <td>
                    <Stack direction="row" spacing={0.25}>
                      {user.status === "active" ? (
                        <IconButton
                          tooltip="Suspend user"
                          size={density === "compact" ? "sm" : "md"}
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
                          size={density === "compact" ? "sm" : "md"}
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
                        size={density === "compact" ? "sm" : "md"}
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
