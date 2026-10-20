"use client";
/**
 * @file components/ui/ScopeSelect.tsx
 * @brief Controlled component for selecting post/event/gallery scope.
 * Supports three options: community-level, subgroup-specific, or private.
 * WCAG 2.1 AA: ARIA labels, keyboard navigation, contrast-compliant.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import FormControl from "@mui/joy/FormControl";
import FormLabel from "@mui/joy/FormLabel";
import Typography from "@mui/joy/Typography";
import Box from "@mui/joy/Box";
import { Select, Option } from "@/components/ui/Select";

export interface ScopeValue {
  visibility: "community" | "subgroup" | "private";
  subgroup_id: string | null;
}

export interface Subgroup {
  id: string;
  name: string;
}

export interface ScopeSelectProps {
  value: ScopeValue;
  onChange: (value: ScopeValue) => void;
  subgroups: Subgroup[];
}

export function ScopeSelect({ value, onChange, subgroups }: ScopeSelectProps) {
  return (
    <FormControl>
      <FormLabel>Share with</FormLabel>
      <Stack direction="column" spacing={1.5}>
        {/* Community option */}
        <Box
          component="label"
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            cursor: "pointer",
            p: 1,
            borderRadius: "sm",
            transition: "background-color 120ms ease",
            "&:hover": {
              backgroundColor: "var(--joy-palette-neutral-softHoverBg)",
            },
          }}
        >
          <input
            type="radio"
            name="scope"
            value="community"
            checked={value.visibility === "community"}
            onChange={() =>
              onChange({ visibility: "community", subgroup_id: null })
            }
            aria-label="Community"
            style={{ cursor: "pointer" }}
          />
          <Typography level="body-sm">Community</Typography>
        </Box>

        {/* Subgroup option with dropdown */}
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1,
          }}
        >
          <Box
            component="label"
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              cursor: "pointer",
              p: 1,
              borderRadius: "sm",
              transition: "background-color 120ms ease",
              "&:hover": {
                backgroundColor: "var(--joy-palette-neutral-softHoverBg)",
              },
            }}
          >
            <input
              type="radio"
              name="scope"
              value="subgroup"
              checked={value.visibility === "subgroup"}
              onChange={() =>
                onChange({ visibility: "subgroup", subgroup_id: null })
              }
              aria-label="A specific group"
              style={{ cursor: "pointer" }}
            />
            <Typography level="body-sm">A specific group</Typography>
          </Box>

          {/* Subgroup dropdown (only visible when subgroup option is selected) */}
          {value.visibility === "subgroup" && (
            <Box sx={{ ml: 4 }}>
              <Select
                value={value.subgroup_id ?? ""}
                onChange={(_e, v) => {
                  onChange({
                    visibility: "subgroup",
                    subgroup_id: (v as string) || null,
                  });
                }}
                placeholder={
                  subgroups.length === 0
                    ? "No groups available"
                    : "Select a group"
                }
                disabled={subgroups.length === 0}
                aria-label="Select a group"
              >
                {subgroups.map((g) => (
                  <Option key={g.id} value={g.id}>
                    {g.name}
                  </Option>
                ))}
              </Select>
            </Box>
          )}
        </Box>

        {/* Private option */}
        <Box
          component="label"
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            cursor: "pointer",
            p: 1,
            borderRadius: "sm",
            transition: "background-color 120ms ease",
            "&:hover": {
              backgroundColor: "var(--joy-palette-neutral-softHoverBg)",
            },
          }}
        >
          <input
            type="radio"
            name="scope"
            value="private"
            checked={value.visibility === "private"}
            onChange={() =>
              onChange({ visibility: "private", subgroup_id: null })
            }
            aria-label="Just me (private)"
            style={{ cursor: "pointer" }}
          />
          <Typography level="body-sm">Just me (private)</Typography>
        </Box>
      </Stack>
    </FormControl>
  );
}

export default ScopeSelect;
