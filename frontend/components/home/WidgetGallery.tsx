"use client";
/**
 * @file components/home/WidgetGallery.tsx
 * @brief Right-side drawer listing widgets not in the current layout.
 *        Controlled — parent (RightRail) toggles `open`. Internally consumes
 *        useHomeLayout to add/reset widgets.
 *
 * @param open      Controlled drawer state.
 * @param onClose   Close handler.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Box from "@mui/joy/Box";
import Divider from "@mui/joy/Divider";
import { Drawer } from "@/components/ui/Drawer";
import { Button } from "@/components/ui/Button";
import { listDefs } from "@/lib/widgets/registry";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useHomeLayout } from "@/hooks/useHomeLayout";

export interface WidgetGalleryProps {
  open: boolean;
  onClose: () => void;
}

export function WidgetGallery({ open, onClose }: WidgetGalleryProps) {
  const confirm = useConfirmDialog((s) => s.confirm);
  const layout = useHomeLayout();
  const presentDefIds = layout.widgets.map((w) => w.defId);
  const available = listDefs().filter((def) => !presentDefIds.includes(def.id));

  const handleAdd = (defId: string) => {
    layout.addWidget(defId);
    onClose();
  };

  const handleReset = async () => {
    const ok = await confirm({
      title: "Reset layout to default?",
      message: "All customisations will be lost.",
      confirmLabel: "Reset",
      tone: "danger",
    });
    if (!ok) return;
    layout.resetToDefault();
    onClose();
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Customize dashboard"
      side="right"
      width={360}
    >
      <Stack
        aria-label="Widget gallery"
        sx={{ height: "100%", display: "flex", flexDirection: "column" }}
      >
        <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
          {available.length === 0 ? (
            <Typography
              level="body-sm"
              textColor="text.tertiary"
              sx={{ textAlign: "center", py: 4 }}
            >
              All widgets are already on your dashboard.
            </Typography>
          ) : (
            <Stack spacing={1.25}>
              <Typography
                level="body-xs"
                sx={{
                  textTransform: "uppercase",
                  letterSpacing: "0.14em",
                  color: "text.tertiary",
                  fontWeight: 600,
                  mb: 0.5,
                }}
              >
                Available widgets
              </Typography>
              {available.map((def) => (
                <Box
                  key={def.id}
                  sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 2,
                    p: 1.5,
                    borderRadius: "md",
                    border: "1px solid",
                    borderColor: "divider",
                    bgcolor: "background.surface",
                    transition: "border-color 150ms",
                    "&:hover": { borderColor: "primary.500" },
                  }}
                >
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography level="title-sm" sx={{ color: "text.primary" }}>
                      {def.title}
                    </Typography>
                    {def.description && (
                      <Typography
                        level="body-xs"
                        textColor="text.tertiary"
                        sx={{ mt: 0.25 }}
                      >
                        {def.description}
                      </Typography>
                    )}
                  </Box>
                  <Button
                    size="sm"
                    variant="outlined"
                    aria-label={`Add ${def.title} widget`}
                    onClick={() => handleAdd(def.id)}
                  >
                    Add
                  </Button>
                </Box>
              ))}
            </Stack>
          )}
        </Box>
        <Box sx={{ p: 2, borderTop: "1px solid", borderColor: "divider" }}>
          <Divider sx={{ mb: 2 }} />
          <Button
            fullWidth
            variant="soft"
            color="neutral"
            onClick={handleReset}
          >
            Reset to default
          </Button>
        </Box>
      </Stack>
    </Drawer>
  );
}

export default WidgetGallery;
