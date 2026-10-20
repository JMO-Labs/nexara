/**
 * @file app/app/admin/page.tsx
 * @brief Admin panel server page wrapper.
 */
import { AdminTabs } from "@/components/admin/AdminTabs";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";

export const metadata = {
  title: "Admin Panel",
};

export default function AdminPage() {
  return (
    <Stack spacing={4}>
      <div>
        <Typography level="h1">Admin Panel</Typography>
        <Typography level="body-md" textColor="text.tertiary">
          Manage community, users, settings, and integrations.
        </Typography>
      </div>
      <AdminTabs />
    </Stack>
  );
}
