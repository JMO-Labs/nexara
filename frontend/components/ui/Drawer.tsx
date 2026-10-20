"use client";
/**
 * @file components/ui/Drawer.tsx
 * @brief Side drawer (right/left/bottom). Joy Drawer base with
 *        framer-motion variants. Used heavily — modals-over-routes.
 */
import * as React from "react";
import JoyDrawer, { type DrawerProps as JoyDrawerProps } from "@mui/joy/Drawer";
import ModalClose from "@mui/joy/ModalClose";
import Typography from "@mui/joy/Typography";
import Box from "@mui/joy/Box";

export interface DrawerProps extends Omit<JoyDrawerProps, "title"> {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  side?: "left" | "right" | "bottom";
  width?: number | string;
  hideClose?: boolean;
}

export function Drawer({
  open,
  onClose,
  title,
  side = "right",
  width = 480,
  hideClose,
  children,
  slotProps,
  ...rest
}: DrawerProps) {
  return (
    <JoyDrawer
      open={open}
      onClose={onClose}
      anchor={side}
      slotProps={{
        ...slotProps,
        content: {
          ...(slotProps?.content ?? {}),
          sx: {
            width: side === "bottom" ? "100%" : width,
            maxWidth: "100%",
            borderTopLeftRadius: side === "right" ? "var(--nx-radius-lg)" : 0,
            borderBottomLeftRadius:
              side === "right" ? "var(--nx-radius-lg)" : 0,
            borderTopRightRadius: side === "left" ? "var(--nx-radius-lg)" : 0,
            borderBottomRightRadius:
              side === "left" ? "var(--nx-radius-lg)" : 0,
            backgroundColor: "background.surface",
          },
        },
      }}
      {...rest}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
        }}
      >
        {title ? (
          <Typography level="h4" sx={{ fontFamily: "var(--font-display)" }}>
            {title}
          </Typography>
        ) : (
          <span />
        )}
        {!hideClose && <ModalClose sx={{ position: "static" }} />}
      </Box>
      <Box sx={{ px: 2, pb: 2, flex: 1, minHeight: 0, overflow: "auto" }}>
        {children}
      </Box>
    </JoyDrawer>
  );
}

export default Drawer;
