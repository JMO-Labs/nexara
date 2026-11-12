"use client";
/**
 * @file components/admin/UsersTab.tsx
 * @brief Admin user management table with search and suspend/restore/delete.
 *        Rows stack into cards on phone.
 */
import { useState } from "react";
import { Check, Loader2, Trash2, X } from "lucide-react";
import {
  useAdminUsers,
  useSuspendUser,
  useRestoreUser,
  useDeleteUser,
} from "@/hooks/useAdmin";
import {
  Badge,
  Button,
  IconButton,
  Input,
  Modal,
  Option,
  Select,
} from "@/components/ui";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/shadcn/table";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  member: "Member",
  viewer: "Viewer",
};

/**
 * @brief Users admin tab.
 * @return tab content
 */
export function UsersTab() {
  const [searchQuery, setSearchQuery] = useState("");
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);
  const [density, setDensity] = useState<"comfortable" | "compact">(
    "comfortable",
  );

  const {
    data: usersPage,
    isLoading,
    error,
  } = useAdminUsers({ q: searchQuery || undefined, limit: 50 });

  const suspendMutation = useSuspendUser();
  const restoreMutation = useRestoreUser();
  const deleteMutation = useDeleteUser();

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2
          role="status"
          aria-label="Loading users"
          className="size-6 motion-safe:animate-spin"
        />
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-2xl border-l-4 border-danger bg-surface p-3"
      >
        Failed to load users
      </div>
    );
  }

  if (!usersPage) return null;

  const handleConfirmDelete = () => {
    if (deletingUserId) {
      deleteMutation.mutate(deletingUserId);
      setDeletingUserId(null);
    }
  };

  const cell = density === "compact" ? "py-1 text-xs" : "py-2 text-sm";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <Input
            type="search"
            aria-label="Search users"
            placeholder="Search by name or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="sm:w-40">
          <Select
            label="Density"
            value={density}
            onValueChange={(v) => setDensity(v as "comfortable" | "compact")}
          >
            <Option value="comfortable">Comfortable</Option>
            <Option value="compact">Compact</Option>
          </Select>
        </div>
      </div>

      {usersPage.items.length === 0 ? (
        <div role="status" className="rounded-2xl bg-surface p-3">
          No users found
        </div>
      ) : (
        <div className="rounded-2xl bg-surface p-2">
          <Table>
            <TableHeader className="max-md:sr-only">
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {usersPage.items.map((user) => (
                <TableRow
                  key={user.id}
                  className="max-md:grid max-md:grid-cols-2 max-md:items-center max-md:gap-x-3"
                >
                  <TableCell
                    className={`${cell} max-md:col-span-2 font-semibold`}
                  >
                    {user.display_name || user.username}
                  </TableCell>
                  <TableCell
                    className={`${cell} max-md:col-span-2 max-md:whitespace-normal max-md:break-all`}
                  >
                    {user.email}
                  </TableCell>
                  <TableCell className={cell}>
                    <Badge tone={user.role === "admin" ? "accent" : "neutral"}>
                      {ROLE_LABEL[user.role] ?? user.role}
                    </Badge>
                  </TableCell>
                  <TableCell className={cell}>{user.status}</TableCell>
                  <TableCell className={`${cell} max-md:col-span-2`}>
                    <div className="flex gap-1">
                      {user.status === "active" ? (
                        <IconButton
                          variant="ghost"
                          aria-label="Suspend user"
                          tooltip="Suspend user"
                          title="Suspend user"
                          onClick={() => suspendMutation.mutate(user.id)}
                        >
                          <X className="size-4" aria-hidden="true" />
                        </IconButton>
                      ) : (
                        <IconButton
                          variant="ghost"
                          aria-label="Restore user"
                          tooltip="Restore user"
                          title="Restore user"
                          onClick={() => restoreMutation.mutate(user.id)}
                        >
                          <Check className="size-4" aria-hidden="true" />
                        </IconButton>
                      )}
                      <IconButton
                        variant="ghost"
                        aria-label="Delete user"
                        tooltip="Delete user"
                        title="Delete user"
                        onClick={() => setDeletingUserId(user.id)}
                      >
                        <Trash2 className="size-4" aria-hidden="true" />
                      </IconButton>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Modal
        open={deletingUserId !== null}
        onClose={() => setDeletingUserId(null)}
        title="Delete user"
        description="Are you sure? This action cannot be undone."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeletingUserId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              loading={deleteMutation.isPending}
            >
              Delete
            </Button>
          </>
        }
      >
        {null}
      </Modal>
    </div>
  );
}
