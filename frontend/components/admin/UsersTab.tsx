"use client";
/**
 * @file components/admin/UsersTab.tsx
 * @brief Admin user management table with search and suspend/restore/delete.
 *        Rows stack into cards on phone.
 */
import { useEffect, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useUI } from "@/stores/ui";
import { Check, Loader2, Trash2, Users, X } from "lucide-react";
import {
  useAdminUsersInfinite,
  useSuspendUser,
  useRestoreUser,
  useDeleteUser,
} from "@/hooks/useAdmin";
import { Badge, Button, EmptyState, IconButton, Modal } from "@/components/ui";
import { Segmented, SearchField, Toolbar } from "@/components/ui/page";
import { AdminNotice } from "./AdminState";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/shadcn/table";

/** @brief Row count above which the table is windowed. */
const VIRTUAL_THRESHOLD = 100;

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  member: "Member",
  viewer: "Viewer",
};

/**
 * @brief Capitalise the first letter of a status code.
 * @param s raw status, e.g. "active"
 * @return sentence-case label, e.g. "Active"
 */
const capitalise = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/**
 * @brief Users admin tab.
 * @return tab content
 */
export function UsersTab() {
  const [searchQuery, setSearchQuery] = useState("");
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);
  const density = useUI((s) => s.density);
  const setDensity = useUI((s) => s.setDensity);
  const scrollRef = useRef<HTMLDivElement>(null);

  const {
    data: usersPage,
    isLoading,
    error,
    refetch,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useAdminUsersInfinite({ q: searchQuery || undefined, limit: 50 });

  const suspendMutation = useSuspendUser();
  const restoreMutation = useRestoreUser();
  const deleteMutation = useDeleteUser();

  const items = usersPage?.items ?? [];
  const virtual = items.length > VIRTUAL_THRESHOLD;
  const rowHeight = density === "compact" ? 40 : 52;
  const virtualizer = useVirtualizer({
    count: virtual ? items.length : 0,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => rowHeight,
    overscan: 10,
  });

  // Fetch the next page when the window nears the end of loaded rows.
  const lastVisible = virtual
    ? (virtualizer.getVirtualItems().at(-1)?.index ?? -1)
    : -1;
  useEffect(() => {
    if (
      virtual &&
      hasNextPage &&
      !isFetchingNextPage &&
      lastVisible >= items.length - 10
    ) {
      fetchNextPage();
    }
  }, [
    virtual,
    hasNextPage,
    isFetchingNextPage,
    lastVisible,
    items.length,
    fetchNextPage,
  ]);

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
      <AdminNotice tone="error">
        <div className="flex items-center justify-between gap-3">
          <p>Failed to load users</p>
          <Button variant="glass" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      </AdminNotice>
    );
  }

  if (!usersPage) return null;

  const handleConfirmDelete = () => {
    if (deletingUserId) {
      deleteMutation.mutate(deletingUserId);
      setDeletingUserId(null);
    }
  };

  const vItems = virtualizer.getVirtualItems();
  const visible = virtual ? vItems.map((v) => items[v.index]) : items;
  const padTop = vItems.length ? vItems[0].start : 0;
  const padBottom = vItems.length
    ? virtualizer.getTotalSize() - vItems[vItems.length - 1].end
    : 0;
  const cell = density === "compact" ? "py-1 text-xs" : "py-2 text-sm";

  return (
    <div className="flex flex-col gap-6">
      <Toolbar className="mb-0">
        <div className="min-w-0 flex-1">
          <SearchField
            label="Search users"
            placeholder="Search by name or email"
            value={searchQuery}
            onChange={setSearchQuery}
          />
        </div>
        <Segmented
          label="Density"
          options={[
            { value: "comfortable", label: "Comfortable" },
            { value: "compact", label: "Compact" },
          ]}
          value={density}
          onChange={(v) => setDensity(v as "comfortable" | "compact")}
        />
      </Toolbar>

      {usersPage.items.length === 0 ? (
        <div role="status">
          <EmptyState compact icon={Users} title="No users found" />
        </div>
      ) : (
        <div
          ref={scrollRef}
          className={cn(virtual && "max-h-[70vh] overflow-y-auto")}
        >
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
              {virtual && padTop > 0 && (
                <tr aria-hidden="true" style={{ height: padTop }} />
              )}
              {visible.map((user) => (
                <TableRow
                  key={user.id}
                  data-index={virtual ? items.indexOf(user) : undefined}
                  ref={virtual ? virtualizer.measureElement : undefined}
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
                  <TableCell className={cell}>
                    <Badge
                      tone={user.status === "active" ? "accent" : "neutral"}
                    >
                      {capitalise(user.status)}
                    </Badge>
                  </TableCell>
                  <TableCell className={`${cell} max-md:col-span-2`}>
                    <div className="flex gap-1">
                      {user.status === "active" ? (
                        <IconButton
                          variant="glass"
                          aria-label="Suspend user"
                          tooltip="Suspend user"
                          onClick={() => suspendMutation.mutate(user.id)}
                        >
                          <X className="size-4" aria-hidden="true" />
                        </IconButton>
                      ) : (
                        <IconButton
                          variant="glass"
                          aria-label="Restore user"
                          tooltip="Restore user"
                          onClick={() => restoreMutation.mutate(user.id)}
                        >
                          <Check className="size-4" aria-hidden="true" />
                        </IconButton>
                      )}
                      <IconButton
                        variant="glass"
                        aria-label="Delete user"
                        tooltip="Delete user"
                        onClick={() => setDeletingUserId(user.id)}
                      >
                        <Trash2 className="size-4" aria-hidden="true" />
                      </IconButton>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {virtual && padBottom > 0 && (
                <tr aria-hidden="true" style={{ height: padBottom }} />
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {hasNextPage && (
        <Button
          variant="ghost"
          className="self-center"
          loading={isFetchingNextPage}
          onClick={() => fetchNextPage()}
        >
          Load more
        </Button>
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
