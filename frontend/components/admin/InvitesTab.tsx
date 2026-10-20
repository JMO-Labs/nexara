"use client";
/**
 * @file components/admin/InvitesTab.tsx
 * @brief Admin invite creation and management.
 */
import { useState } from "react";
import { Trash2 } from "lucide-react";
import {
  useInvites,
  useCreateInvite,
  useRevokeInvite,
} from "@/hooks/useInvites";
import {
  Button,
  Card,
  IconButton,
  Input,
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
import { AdminLoading, AdminNotice, stackTable } from "./AdminState";

export function InvitesTab() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>("member");

  const { data: invites, isLoading, error } = useInvites();
  const createMutation = useCreateInvite();
  const revokeMutation = useRevokeInvite();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      createMutation.mutate({ email, role });
      setEmail("");
      setRole("member");
    }
  };

  if (isLoading) return <AdminLoading />;

  if (error) {
    return <AdminNotice tone="error">Failed to load invites</AdminNotice>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-12">
      <Card className="p-4 md:col-span-5">
        <h3 className="mb-3 text-lg font-semibold">Create invite</h3>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <Input
            type="email"
            label="Email address"
            placeholder="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Select label="Role" value={role} onValueChange={setRole}>
            <Option value="admin">Admin</Option>
            <Option value="member">Member</Option>
            <Option value="viewer">Viewer</Option>
          </Select>
          <Button type="submit" loading={createMutation.isPending}>
            Send invite
          </Button>
        </form>
      </Card>

      <div className="md:col-span-7">
        {invites && invites.length > 0 ? (
          <Card className="p-4">
            <h3 className="mb-3 text-lg font-semibold">Pending invites</h3>
            <Table>
              <TableHeader className={stackTable.head}>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-12">
                    <span className="sr-only">Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invites.map((invite) => (
                  <TableRow key={invite.id} className={stackTable.row}>
                    <TableCell data-label="Email" className={stackTable.cell}>
                      {invite.email}
                    </TableCell>
                    <TableCell data-label="Role" className={stackTable.cell}>
                      {invite.role}
                    </TableCell>
                    <TableCell data-label="Status" className={stackTable.cell}>
                      {invite.used_at ? "Used" : "Pending"}
                    </TableCell>
                    <TableCell className={stackTable.cell}>
                      <IconButton
                        size="sm"
                        variant="ghost"
                        className="text-danger"
                        onClick={() => revokeMutation.mutate(invite.id)}
                        disabled={revokeMutation.isPending}
                        aria-label={`Revoke invite for ${invite.email}`}
                      >
                        <Trash2 className="size-4" aria-hidden="true" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        ) : (
          <AdminNotice>No pending invites</AdminNotice>
        )}
      </div>
    </div>
  );
}
