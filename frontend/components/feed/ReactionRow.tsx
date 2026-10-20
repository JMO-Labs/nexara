"use client";
/**
 * @file components/feed/ReactionRow.tsx
 * @brief Reactions chip strip + add-reaction trigger + comment count.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import Popover from "@mui/joy/Tooltip";
import { motion } from "framer-motion";
import { ChatBubbleLeftIcon, FaceSmileIcon } from "@heroicons/react/24/outline";
import { IconButton } from "@/components/ui";
import type { ReactionSummary } from "@/lib/api/posts";

const QUICK = ["👍", "❤️", "😂", "🎉", "😮", "🙏"];

export interface ReactionRowProps {
  reactions: ReactionSummary[];
  commentCount: number;
  onReact: (emoji: string) => void;
  onCommentClick?: () => void;
}

interface ReactionScaleState {
  [emoji: string]: boolean;
}

export function ReactionRow({
  reactions,
  commentCount,
  onReact,
  onCommentClick,
}: ReactionRowProps) {
  const [open, setOpen] = React.useState(false);
  const [scalingEmoji, setScalingEmoji] = React.useState<ReactionScaleState>(
    {},
  );
  const [displayCounts, setDisplayCounts] = React.useState<
    Record<string, number>
  >({});

  const handleReact = (emoji: string) => {
    setScalingEmoji((s) => ({ ...s, [emoji]: true }));
    setTimeout(() => setScalingEmoji((s) => ({ ...s, [emoji]: false })), 200);
    onReact(emoji);
  };

  // Animate count changes
  React.useEffect(() => {
    reactions.forEach((r) => {
      if (!displayCounts[r.emoji]) {
        setDisplayCounts((c) => ({ ...c, [r.emoji]: r.count }));
      } else {
        const start = displayCounts[r.emoji];
        const end = r.count;
        if (start === end) return;

        const startTime = Date.now();
        const duration = 250;

        const animateCount = () => {
          const elapsed = Date.now() - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const current = Math.round(start + (end - start) * progress);
          setDisplayCounts((c) => ({ ...c, [r.emoji]: current }));

          if (progress < 1) {
            requestAnimationFrame(animateCount);
          }
        };

        const frameId = requestAnimationFrame(animateCount);
        return () => cancelAnimationFrame(frameId);
      }
    });
  }, [reactions]);

  return (
    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
      {reactions.map((r) => (
        <motion.div
          key={r.emoji}
          animate={
            scalingEmoji[r.emoji] ? { scale: [1, 1.2, 1] } : { scale: 1 }
          }
          transition={{ duration: 0.2, ease: "easeOut" }}
        >
          <Box
            role="button"
            aria-pressed={r.reacted_by_me}
            aria-label={`${r.emoji} reaction, ${r.count} ${r.count === 1 ? "person" : "people"}`}
            onClick={() => handleReact(r.emoji)}
            sx={{
              display: "inline-flex",
              alignItems: "center",
              px: 0.75,
              py: 0.25,
              borderRadius: "sm",
              cursor: "pointer",
              gap: 0.5,
              bgcolor: r.reacted_by_me ? "primary.softBg" : "background.level1",
              color: r.reacted_by_me ? "primary.plainColor" : "text.primary",
              border: "1px solid",
              borderColor: r.reacted_by_me
                ? "primary.outlinedBorder"
                : "divider",
              fontSize: "0.875rem",
              transition: "background 200ms",
              "&:hover": {
                bgcolor: r.reacted_by_me
                  ? "primary.plainHoverBg"
                  : "background.level2",
              },
            }}
          >
            {r.emoji} {displayCounts[r.emoji] ?? r.count}
          </Box>
        </motion.div>
      ))}
      <Box sx={{ position: "relative" }}>
        <Popover title="Add reaction" placement="top">
          <IconButton
            aria-label="Add reaction"
            size="sm"
            variant="plain"
            onClick={() => setOpen((v) => !v)}
          >
            <FaceSmileIcon width={18} />
          </IconButton>
        </Popover>
        {open ? (
          <Box
            sx={{
              position: "absolute",
              bottom: "100%",
              left: 0,
              mb: 0.5,
              p: 0.5,
              display: "flex",
              gap: 0.25,
              backgroundColor: "background.popup",
              borderRadius: "md",
              boxShadow: "md",
              zIndex: 10,
            }}
            onMouseLeave={() => setOpen(false)}
          >
            {QUICK.map((e) => (
              <IconButton
                key={e}
                size="sm"
                variant="plain"
                onClick={() => {
                  onReact(e);
                  setOpen(false);
                }}
              >
                <span style={{ fontSize: 18 }}>{e}</span>
              </IconButton>
            ))}
          </Box>
        ) : null}
      </Box>
      <Box sx={{ flexGrow: 1 }} />
      <IconButton
        aria-label="Comments"
        size="sm"
        variant="plain"
        onClick={onCommentClick}
      >
        <ChatBubbleLeftIcon width={18} />
      </IconButton>
      <Typography level="body-xs" textColor="text.tertiary">
        {commentCount}
      </Typography>
    </Stack>
  );
}

export default ReactionRow;
