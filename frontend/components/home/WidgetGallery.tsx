"use client";
/**
 * @file components/home/WidgetGallery.tsx
 * @brief Floating "+ Add widget" button that opens a right-side drawer
 *        listing all registered widgets not yet in the current layout.
 * @param presentDefIds Set of defIds already in the layout (to exclude).
 * @param onAdd         Called with the defId to add.
 * @param onReset       Called to reset layout to default.
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

export interface WidgetGalleryProps {
  presentDefIds: string[];
  onAdd: (defId: string) => void;
  onReset: () => void;
}

export function WidgetGallery({
  presentDefIds,
  onAdd,
  onReset,
}: WidgetGalleryProps) {
  const [open, setOpen] = React.useState(false);
  const confirm = useConfirmDialog((s) => s.confirm);

  const available = listDefs().filter((def) => !presentDefIds.includes(def.id));

  return (
    <>
      {/* Floating add button */}
      <button
        type="button"
        aria-label="Add widget"
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-30 flex items-center gap-2 px-4 py-2.5 rounded-full bg-indigo-600 text-white text-sm font-semibold shadow-lg hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)] transition-colors"
      >
        <svg
          aria-hidden="true"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        >
          <line x1="8" y1="2" x2="8" y2="14" />
          <line x1="2" y1="8" x2="14" y2="8" />
        </svg>
        Add widget
      </button>

      {/* Drawer */}
      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        title="Widget gallery"
        side="right"
        width={360}
      >
        <Stack
          aria-label="Widget gallery"
          sx={{ height: "100%", display: "flex", flexDirection: "column" }}
        >
          {/* Widget list */}
          <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
            {available.length === 0 ? (
              <Typography
                level="body-sm"
                textColor="text.tertiary"
                sx={{ textAlign: "center", py: 4 }}
              >
                All widgets are already on your page.
              </Typography>
            ) : (
              <Stack spacing={1.5}>
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
                    }}
                  >
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography level="title-sm">{def.title}</Typography>
                      {def.description && (
                        <Typography level="body-xs" textColor="text.tertiary">
                          {def.description}
                        </Typography>
                      )}
                    </Box>
                    <Button
                      size="sm"
                      variant="outlined"
                      aria-label={`Add ${def.title} widget`}
                      onClick={() => {
                        onAdd(def.id);
                        setOpen(false);
                      }}
                    >
                      Add
                    </Button>
                  </Box>
                ))}
              </Stack>
            )}
          </Box>

          {/* Footer */}
          <Box sx={{ p: 2, borderTop: "1px solid", borderColor: "divider" }}>
            <Divider sx={{ mb: 2 }} />
            <Button
              fullWidth
              variant="soft"
              color="neutral"
              onClick={async () => {
                const ok = await confirm({
                  title: "Reset layout to default?",
                  message: "All customisations will be lost.",
                  confirmLabel: "Reset",
                  tone: "danger",
                });
                if (!ok) return;
                onReset();
                setOpen(false);
              }}
            >
              Reset to default
            </Button>
          </Box>
        </Stack>
      </Drawer>
    </>
  );
}

export default WidgetGallery;
