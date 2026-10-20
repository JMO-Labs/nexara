/**
 * @file app/page.tsx
 * @brief Phase 0 placeholder landing. Confirms theme/fonts/providers
 *        wire up. Replaced by (marketing)/page.tsx in Phase 2.
 */
"use client";
import { Box, Stack, Typography, Button, Sheet, Chip } from "@mui/joy";
import Link from "next/link";

export default function Home() {
  return (
    <Box
      component="main"
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        px: 3,
        py: 8,
      }}
    >
      <Sheet
        variant="outlined"
        sx={{
          maxWidth: 720,
          width: "100%",
          p: { xs: 4, sm: 6 },
          borderRadius: "lg",
          boxShadow: "md",
          display: "flex",
          flexDirection: "column",
          gap: 3,
        }}
      >
        <Chip
          size="sm"
          variant="soft"
          color="warning"
          sx={{ alignSelf: "flex-start" }}
        >
          Phase 0 · bootstrap
        </Chip>
        <Typography level="h1" sx={{ fontFamily: "display" }}>
          Nexara, rewritten.
        </Typography>
        <Typography level="body-md" color="neutral">
          Warm Editorial palette online. Fraunces &amp; Geist served via{" "}
          <Typography component="code" fontFamily="code">
            next/font
          </Typography>
          . Joy CSS-vars, TanStack Query, Zustand, Framer Motion, next-themes
          mounted.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <Button component={Link} href="/login" size="lg">
            Sign in
          </Button>
          <Button
            component={Link}
            href="/app"
            size="lg"
            variant="outlined"
            color="neutral"
          >
            Enter app
          </Button>
        </Stack>
      </Sheet>
    </Box>
  );
}
