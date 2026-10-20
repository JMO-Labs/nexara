"use client";
/**
 * @file components/ui/CommandPalette.tsx
 * @brief ⌘K command palette shell. Phase 1 ships UI + keyboard plumbing
 *        + scoped result list contract. Result providers (search, nav,
 *        actions) wire in Phase 6.
 *
 * Inner state (query, active index) lives in PaletteContent which only
 * mounts while the palette is open — fresh mount handles the reset
 * without a setState-in-effect cycle.
 */
import * as React from "react";
import JoyModal from "@mui/joy/Modal";
import ModalDialog from "@mui/joy/ModalDialog";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import { motion } from "framer-motion";
import { useUI } from "@/stores/ui";
import { modalVariants } from "./motion";

export type CommandItem = {
  id: string;
  label: string;
  hint?: string;
  group?: string;
  keywords?: string[];
  /** When true, skip client-side substring filter (server already filtered). */
  external?: boolean;
  onSelect: () => void;
};

export interface CommandPaletteProps {
  items: CommandItem[];
  placeholder?: string;
  onQueryChange?: (q: string) => void;
}

function PaletteContent({
  items,
  placeholder,
  close,
  onQueryChange,
}: {
  items: CommandItem[];
  placeholder: string;
  close: () => void;
  onQueryChange?: (q: string) => void;
}) {
  const [q, setQ] = React.useState("");
  const [active, setActive] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const filtered = React.useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((it) => {
      if (it.external) return true;
      const hay = [it.label, it.hint, it.group, ...(it.keywords ?? [])]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(needle);
    });
  }, [items, q]);

  const grouped = React.useMemo(() => {
    const map = new Map<string, CommandItem[]>();
    for (const it of filtered) {
      const g = it.group ?? "Results";
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(it);
    }
    return Array.from(map.entries());
  }, [filtered]);

  function pick(i: number) {
    const it = filtered[i];
    if (!it) return;
    it.onSelect();
    close();
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(filtered.length - 1, a + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      pick(active);
    } else if (e.key === "Escape") {
      close();
    }
  }

  let runningIndex = -1;
  return (
    <motion.div
      variants={modalVariants}
      initial="hidden"
      animate="show"
      style={{ display: "contents" }}
    >
      <Box sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}>
        <input
          ref={inputRef}
          autoFocus
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setActive(0);
            onQueryChange?.(e.target.value);
          }}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          aria-label="Command palette"
          style={{
            width: "100%",
            border: "none",
            outline: "none",
            background: "transparent",
            fontFamily: "var(--font-body)",
            fontSize: "1.05rem",
            color: "var(--nx-palette-text-primary)",
          }}
        />
      </Box>
      <Box
        sx={{ maxHeight: 420, overflow: "auto", py: 1 }}
        aria-live="polite"
        aria-atomic="true"
      >
        {filtered.length === 0 && (
          <Typography
            level="body-sm"
            sx={{ p: 3, textAlign: "center", color: "text.tertiary" }}
          >
            Nothing matches.
          </Typography>
        )}
        {grouped.map(([group, list]) => (
          <Box key={group} sx={{ pb: 1 }}>
            <Typography
              level="body-xs"
              sx={{
                px: 2,
                pt: 1,
                pb: 0.5,
                fontFamily: "var(--font-display)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "text.tertiary",
              }}
            >
              {group}
            </Typography>
            {list.map((it) => {
              runningIndex += 1;
              const idx = runningIndex;
              const isActive = idx === active;
              return (
                <Box
                  key={it.id}
                  role="option"
                  aria-selected={isActive}
                  onMouseEnter={() => setActive(idx)}
                  onClick={() => pick(idx)}
                  sx={{
                    px: 2,
                    py: 1,
                    mx: 1,
                    borderRadius: "sm",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    backgroundColor: isActive
                      ? "background.level1"
                      : "transparent",
                  }}
                >
                  <Typography level="body-md">{it.label}</Typography>
                  {it.hint && (
                    <Typography level="body-xs" sx={{ color: "text.tertiary" }}>
                      {it.hint}
                    </Typography>
                  )}
                </Box>
              );
            })}
          </Box>
        ))}
      </Box>
    </motion.div>
  );
}

export function CommandPalette({
  items,
  placeholder = "Search or jump to…",
  onQueryChange,
}: CommandPaletteProps) {
  const open = useUI((s) => s.commandPaletteOpen);
  const setOpen = useUI((s) => s.setCommandPaletteOpen);

  React.useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!useUI.getState().commandPaletteOpen);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  if (!open) return null;
  return (
    <JoyModal open onClose={() => setOpen(false)}>
      <ModalDialog
        sx={{
          maxWidth: 640,
          width: "calc(100vw - 32px)",
          p: 0,
          overflow: "hidden",
          borderRadius: "lg",
        }}
      >
        <PaletteContent
          items={items}
          placeholder={placeholder}
          close={() => setOpen(false)}
          onQueryChange={onQueryChange}
        />
      </ModalDialog>
    </JoyModal>
  );
}

export default CommandPalette;
