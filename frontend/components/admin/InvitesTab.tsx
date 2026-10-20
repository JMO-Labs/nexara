"use client";
/**
 * @file components/admin/InvitesTab.tsx
 * @brief Admin invite creation and management.
 */
import { useState } from "react";
import {
  useInvites,
  useCreateInvite,
  useRevokeInvite,
} from "@/hooks/useInvites";
import Stack from "@mui/joy/Stack";
import Grid from "@mui/joy/Grid";
import Input from "@mui/joy/Input";
import Select from "@mui/joy/Select";
import Option from "@mui/joy/Option";
import Button from "@mui/joy/Button";
import IconButton from "@mui/joy/IconButton";
import Card from "@mui/joy/Card";
import Table from "@mui/joy/Table";
import Typography from "@mui/joy/Typography";
import CircularProgress from "@mui/joy/CircularProgress";
import Alert from "@mui/joy/Alert";
import { TrashIcon } from "@heroicons/react/24/outline";

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
    <Grid container spacing={2}>
      {/* Form: 5/12 on desktop, full width on mobile */}
      <Grid xs={12} md={5}>
        <Card variant="soft">
          <Stack spacing={2}>
            <Typography level="title-md">Create Invite</Typography>
            <form onSubmit={handleSubmit}>
              <Stack spacing={1.5}>
                <Input
                  type="email"
                  placeholder="Email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  size="sm"
                />
                <Select
                  value={role}
                  onChange={(_, val) => val && setRole(val)}
                  size="sm"
                >
                  <Option value="admin">Admin</Option>
                  <Option value="member">Member</Option>
                  <Option value="viewer">Viewer</Option>
                </Select>
                <Button
                  type="submit"
                  loading={createMutation.isPending}
                  size="sm"
                >
                  Send Invite
                </Button>
              </Stack>
            </form>
          </Stack>
        </Card>
      </Grid>

      {/* List: 7/12 on desktop, full width on mobile */}
      <Grid xs={12} md={7}>
        {invites && invites.length > 0 ? (
          <Card variant="outlined">
            <Typography level="title-md" sx={{ mb: 1.5 }}>
              Pending Invites
            </Typography>
            <Table
              stripe="odd"
              hoverRow
              sx={{
                "--TableCell-paddingX": "0.75rem",
                "--TableCell-paddingY": "0.375rem",
                fontSize: "0.875rem",
              }}
            >
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th style={{ width: "40px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {invites.map((invite) => (
                  <tr key={invite.id}>
                    <td>
                      <Typography level="body-xs">{invite.email}</Typography>
                    </td>
                    <td>
                      <Typography level="body-xs">{invite.role}</Typography>
                    </td>
                    <td>
                      <Typography
                        level="body-xs"
                        color={invite.used_at ? "success" : "warning"}
                      >
                        {invite.used_at ? "Used" : "Pending"}
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
                        <TrashIcon width={14} height={14} />
                      </IconButton>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        ) : (
          <Card variant="soft">
            <Alert color="primary" variant="plain">
              No pending invites
            </Alert>
          </Card>
        )}
      </Grid>
    </Grid>
  );
}
