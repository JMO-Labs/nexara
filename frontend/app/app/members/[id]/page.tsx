/**
 * @file app/app/members/[id]/page.tsx
 * @brief Member profile page with galleries tab.
 */
"use client";

import { useParams, useSearchParams } from "next/navigation";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Sheet from "@mui/joy/Sheet";
import { Tabs, TabList, Tab, TabPanel } from "@/components/ui/Tabs";
import { MemberGalleriesTab } from "@/components/members/MemberGalleriesTab";

const TABS = [{ id: "galleries", label: "Galleries" }];

export default function MemberProfilePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const userId = params.id as string;
  const currentTab = searchParams.get("tab") || "galleries";

  return (
    <Sheet
      sx={{
        flex: 1,
        width: "100%",
        mx: "auto",
        px: { xs: 2, md: 6 },
        py: { xs: 2, md: 3 },
        borderRadius: { xs: "sm", md: "md" },
      }}
    >
      <Stack spacing={3}>
        <div>
          <Typography level="h1" component="h1">
            Member Profile
          </Typography>
          <Typography level="body-md" color="neutral">
            User ID: {userId}
          </Typography>
        </div>

        <Tabs
          value={currentTab}
          sx={{
            "--Tabs-gap": "0px",
            "--Tab-minHeight": "48px",
          }}
        >
          <TabList
            disableUnderline
            sx={{
              borderBottom: "1px solid",
              borderColor: "divider",
              display: "flex",
              overflow: "auto",
            }}
          >
            {TABS.map(({ id, label }) => (
              <Tab
                key={id}
                value={id}
                sx={{
                  flexShrink: 0,
                  px: 2,
                  py: 1.5,
                  "&:hover": {
                    backgroundColor: "rgba(0, 0, 0, 0.05)",
                  },
                }}
              >
                {label}
              </Tab>
            ))}
          </TabList>

          {TABS.map(({ id }) => (
            <TabPanel key={id} value={id} sx={{ px: 0, py: 3 }}>
              {id === "galleries" && <MemberGalleriesTab userId={userId} />}
            </TabPanel>
          ))}
        </Tabs>
      </Stack>
    </Sheet>
  );
}
