/**
 * @file app/(auth)/layout.tsx
 * @brief Split-screen auth shell: editorial brand panel (left) + form (right).
 *        Collapses to single column on mobile.
 */
import { Suspense, type ReactNode } from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Sheet from "@mui/joy/Sheet";
import Link from "next/link";
import { ToastRoot } from "@/components/ui/Toast";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        minHeight: "100dvh",
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "5fr 7fr" },
      }}
    >
      <Sheet
        variant="solid"
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          justifyContent: "space-between",
          p: 6,
          // Panel bg uses palette vars that flip per theme (dark in light
          // mode, light in dark mode). Text follows the *body* bg — the
          // inverse of `text.primary` — so it always contrasts the panel.
          background:
            "linear-gradient(155deg, var(--nx-palette-primary-700), var(--nx-palette-neutral-800))",
          color: "var(--nx-palette-background-body)",
        }}
      >
        <Box>
          <Typography
            level="h2"
            sx={{ fontFamily: "var(--font-display)", color: "inherit" }}
          >
            Nexara
          </Typography>
          <Typography
            level="body-sm"
            sx={{ color: "inherit", opacity: 0.8, mt: 1 }}
          >
            A warm home for the communities you love.
          </Typography>
        </Box>
        <Stack spacing={2} sx={{ maxWidth: 360 }}>
          <Typography
            level="h3"
            sx={{
              fontFamily: "var(--font-display)",
              color: "inherit",
              lineHeight: 1.15,
            }}
          >
            Gather. Plan. Remember.
          </Typography>
          <Typography level="body-md" sx={{ color: "inherit", opacity: 0.85 }}>
            Threaded conversation, shared albums, events, and traditions —
            self-hosted, ad-free, yours.
          </Typography>
        </Stack>
        <Typography level="body-xs" sx={{ color: "inherit", opacity: 0.65 }}>
          © {new Date().getFullYear()} Nexara · self-hosted ·{" "}
          <Link
            href="/"
            style={{ color: "inherit", textDecoration: "underline" }}
          >
            About
          </Link>
        </Typography>
      </Sheet>

      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: { xs: 3, sm: 5 },
        }}
      >
        <Box sx={{ width: "100%", maxWidth: 440 }}>
          <Suspense>{children}</Suspense>
        </Box>
      </Box>

      <ToastRoot />
    </Box>
  );
}
