"use client";
/**
 * @file app/app/media/page.tsx
 * @brief Media manager: upload zone + recent uploads grid.
 *
 * Backend has no media-list endpoint; uploaded items are tracked in
 * component-local state for the session. Persistence comes via galleries.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import { UploadZone } from "@/components/media/UploadZone";
import { MediaGrid } from "@/components/media/MediaGrid";
import type { MediaItem } from "@/lib/api/media";

export default function MediaPage() {
  const [recent, setRecent] = React.useState<MediaItem[]>([]);
  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1200, mx: "auto" }}>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ mb: 3 }}
      >
        <Typography level="h2" sx={{ fontFamily: "var(--font-display)" }}>
          Media
        </Typography>
      </Stack>
      <Stack spacing={3}>
        <UploadZone onComplete={(m) => setRecent((cur) => [m, ...cur])} />
        <Box>
          <Typography
            level="title-sm"
            sx={{
              fontFamily: "var(--font-display)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              color: "text.tertiary",
              mb: 1.5,
            }}
          >
            Recent uploads
          </Typography>
          <MediaGrid items={recent} />
        </Box>
      </Stack>
    </Box>
  );
}
