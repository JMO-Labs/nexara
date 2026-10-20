/**
 * @file components/feed/PromptPostCard.tsx
 * @brief Specialized card for prompt posts with response count, live refresh, and interest hints.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import { SparklesIcon, FlagIcon } from "@heroicons/react/24/outline";
import { Button, Card, Chip } from "@/components/ui";
import { usePromptResponses } from "@/hooks/usePromptResponses";
import type { PromptPost } from "@/lib/api/prompts";

export interface PromptPostCardProps {
  post: PromptPost;
  onReply?: (promptId: string) => void;
}

export const PromptPostCard: React.FC<PromptPostCardProps> = ({
  post,
  onReply,
}) => {
  // Use live response count via refetch interval
  const { data: responseData } = usePromptResponses(post.id);
  const displayCount = responseData?.response_count ?? post.response_count;

  // Track previous count for pulse animation
  const [prevCount, setPrevCount] = React.useState(post.response_count);
  const shouldPulse = displayCount > prevCount;

  // Update previous count when display count changes
  // This will cause a re-render with the animation visible
  React.useLayoutEffect(() => {
    if (displayCount > prevCount) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPrevCount(displayCount);
    }
    // Only watch displayCount to avoid circular dependency
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayCount]);

  const isInterestCapture = post.prompt.prompt_type === "interest_capture";

  return (
    <Card
      sx={{
        p: 2,
        borderLeft: "3px solid",
        borderLeftColor: "primary.main",
        backgroundColor:
          "rgba(var(--joy-palette-primary-mainChannel, 59 89 152) / 0.04)",
        position: "relative",
      }}
    >
      {/* Pinned icon in top-right */}
      {post.is_pinned && (
        <div
          data-testid="pinned-icon"
          style={{
            position: "absolute",
            top: 12,
            right: 12,
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          <FlagIcon
            width={16}
            height={16}
            style={{ flexShrink: 0, color: "var(--joy-palette-primary-main)" }}
          />
        </div>
      )}

      <Stack spacing={2}>
        {/* Top bar: subgroup chip */}
        {post.subgroup_name && (
          <Stack direction="row" spacing={1}>
            <Chip size="sm" variant="soft" color="neutral">
              {post.subgroup_name}
            </Chip>
          </Stack>
        )}

        {/* Prompt question in display font, italic, 18px */}
        <Typography
          level="h4"
          sx={{
            fontStyle: "italic",
            fontSize: "18px",
            fontWeight: 600,
            lineHeight: 1.4,
          }}
        >
          {post.prompt.title}
        </Typography>

        {/* Interest capture hint (if applicable) */}
        {isInterestCapture && post.prompt.interest_capture_hint && (
          <Stack
            direction="row"
            spacing={0.75}
            sx={{
              alignItems: "center",
              p: 1,
              borderRadius: "md",
              backgroundColor:
                "rgba(var(--joy-palette-primary-mainChannel, 59 89 152) / 0.08)",
            }}
          >
            <SparklesIcon width={14} height={14} style={{ flexShrink: 0 }} />
            <Typography
              level="body-xs"
              sx={{ fontStyle: "italic", color: "text.secondary" }}
            >
              {post.prompt.interest_capture_hint}
            </Typography>
          </Stack>
        )}

        {/* Response count chip with pulse + ARIA live region */}
        <Stack
          direction="row"
          spacing={1}
          sx={{
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div
            role="status"
            aria-live="polite"
            aria-atomic="true"
            style={{
              animation: shouldPulse ? "pulse 0.6s ease-out" : "none",
            }}
          >
            <style>
              {`
                @keyframes pulse {
                  0% { opacity: 1; }
                  50% { opacity: 0.6; }
                  100% { opacity: 1; }
                }
              `}
            </style>
            <Chip
              size="sm"
              variant="soft"
              color="neutral"
              slotProps={{
                root: {
                  style: {
                    cursor: "default",
                  },
                },
              }}
            >
              {`${displayCount} ${displayCount === 1 ? "response" : "responses"}`}
            </Chip>
          </div>

          {/* Reply button — filled brand primary (vs ghost on normal posts) */}
          <Button
            variant="solid"
            color="primary"
            size="sm"
            onClick={() => onReply?.(post.prompt.id)}
          >
            Reply
          </Button>
        </Stack>
      </Stack>
    </Card>
  );
};

export default PromptPostCard;
