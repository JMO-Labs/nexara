"use client";
/**
 * @file components/admin/InvitesTab.tsx
 * @brief Admin invite creation and management.
 */
import { useState } from "react";
import { MailPlus, Trash2 } from "lucide-react";
import {
  useInvites,
  useCreateInvite,
  useRevokeInvite,
} from "@/hooks/useInvites";
import {
  Badge,
  Button,
  EmptyState,
  IconButton,
  Input,
  Option,
  Select,
} from "@/components/ui";
import { Panel } from "@/components/ui/page";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/shadcn/table";
import { AGE_GROUPS, AGE_LABEL } from "@/lib/api/ageGroups";
import { AdminLoading, AdminNotice, stackTable } from "./AdminState";

/**
 * @brief Capitalise the first letter of a code, e.g. "member" -> "Member".
 * @param s raw value
 * @return sentence-case label
 */
const capitalise = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/**
 * @brief Invite creation form beside the invite list.
 * @return tab content
 */
export function InvitesTab() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>("member");
  const [age, setAge] = useState("none");

  const { data: invites, isLoading, error } = useInvites();
  const createMutation = useCreateInvite();
  const revokeMutation = useRevokeInvite();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      createMutation.mutate({
        email,
        role,
        ...(age !== "none" ? { age_group: age } : {}),
      });
      setEmail("");
      setRole("member");
      setAge("none");
    }
  };

  if (isLoading) return <AdminLoading />;

  if (error) {
    return <AdminNotice tone="error">Failed to load invites</AdminNotice>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-[360px_1fr]">
      <Panel as="div" title="Create invite" className="md:self-start">
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
          <Select label="Age group" value={age} onValueChange={setAge}>
            <Option value="none">{AGE_LABEL.unknown}</Option>
            {AGE_GROUPS.map((g) => (
              <Option key={g} value={g}>
                {AGE_LABEL[g]}
              </Option>
            ))}
          </Select>
          <Button type="submit" loading={createMutation.isPending}>
            Send invite
          </Button>
        </form>
      </Panel>

      <div>
        {invites && invites.length > 0 ? (
          <Panel as="div" title="Invites">
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
                      <Badge>{capitalise(invite.role)}</Badge>
                    </TableCell>
                    <TableCell data-label="Status" className={stackTable.cell}>
                      <Badge tone={invite.used_at ? "neutral" : "accent"}>
                        {invite.used_at ? "Used" : "Pending"}
                      </Badge>
                    </TableCell>
                    <TableCell className={stackTable.cell}>
                      <IconButton
                        size="sm"
                        variant="glass"
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
          </Panel>
        ) : (
          <Panel as="div" title="Invites">
            <EmptyState
              compact
              icon={MailPlus}
              title="No invites yet"
              description="Send an invite to bring someone into the community."
            />
          </Panel>
        )}
      </div>
    </div>
  );
}
